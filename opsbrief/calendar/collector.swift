import Foundation
import EventKit

// Программа только читает события; запись в календарь не выполняется.
let store = EKEventStore()
var granted = false
var finished = false
var accessError: Error?
if #available(macOS 14.0, *) {
    store.requestFullAccessToEvents { ok, error in
        granted = ok; accessError = error; finished = true
    }
} else {
    store.requestAccess(to: .event) { ok, error in
        granted = ok; accessError = error; finished = true
    }
}
// Не блокируем главный поток semaphore: системный запрос может требовать main runloop.
let deadline = Date().addingTimeInterval(90)
while !finished && Date() < deadline {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.1))
}
guard finished && granted else {
    fputs("Нет доступа к календарю macOS: \(accessError?.localizedDescription ?? "разрешение не предоставлено или истёк тайм-аут")\n", stderr)
    exit(2)
}

let args = Array(CommandLine.arguments.dropFirst())
let listMode = args.contains("--list")
func argument(_ name: String) -> String? {
    guard let i = args.firstIndex(of: name), i + 1 < args.count else { return nil }
    return args[i + 1]
}
let calendars = store.calendars(for: .event)
let encoder = JSONSerialization.self
func emit(_ payload: Any) {
    guard let data = try? encoder.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]),
          let output = String(data: data, encoding: .utf8) else {
        fputs("Ошибка сериализации JSON\n", stderr); exit(3)
    }
    print(output)
}
if listMode {
    emit(calendars.map { ["id": $0.calendarIdentifier, "title": $0.title, "source": $0.source.title] })
    exit(0)
}
guard let idsText = argument("--ids"), !idsText.isEmpty else {
    fputs("Укажи --ids ID1,ID2 (сначала вызови --list)\n", stderr); exit(2)
}
let ids = Set(idsText.split(separator: ",").map(String.init))
let selected = calendars.filter { ids.contains($0.calendarIdentifier) }
guard selected.count == ids.count else {
    fputs("Один или несколько выбранных календарей не найдены. Повтори --list и выбор.\n", stderr); exit(2)
}

let dayText = argument("--date") ?? String(ISO8601DateFormatter().string(from: Date()).prefix(10))
let dayFormatter = DateFormatter()
dayFormatter.locale = Locale(identifier: "en_US_POSIX")
dayFormatter.calendar = Calendar(identifier: .gregorian)
dayFormatter.timeZone = TimeZone.current
dayFormatter.dateFormat = "yyyy-MM-dd"
guard let day = dayFormatter.date(from: dayText),
      let interval = Calendar.current.dateInterval(of: .day, for: day) else {
    fputs("Некорректная дата: ожидается YYYY-MM-DD\n", stderr); exit(2)
}
let formatter = ISO8601DateFormatter()
formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
formatter.timeZone = TimeZone.current
let predicate = store.predicateForEvents(withStart: interval.start, end: interval.end, calendars: selected)
let events: [[String: Any]] = store.events(matching: predicate)
    .filter { $0.status != .canceled }
    .sorted { $0.startDate < $1.startDate }
    .map { event in
        [
            "id": event.eventIdentifier ?? "",
            "title": event.title ?? "Без названия",
            "start": formatter.string(from: event.startDate),
            "end": formatter.string(from: event.endDate),
            "all_day": event.isAllDay,
            "calendar_id": event.calendar.calendarIdentifier,
            "calendar": event.calendar.title,
            "location": event.location ?? ""
        ]
    }
emit(["date": dayText, "timezone": TimeZone.current.identifier, "events": events])
