import UserNotifications

let arguments = CommandLine.arguments

if arguments.count == 4 {
    let title = arguments[1]
    let subtitle = arguments[2]
    let body = arguments[3]

    scheduleNotification(title: title, subtitle: subtitle, body: body)
} else {
    print("Invalid arguments")
}

func scheduleNotification(title: String, subtitle: String, body: String) {
    let content = UNMutableNotificationContent()
    content.title = title
    content.subtitle = subtitle
    content.body = body

    let trigger = UNTimeIntervalNotificationTrigger(timeInterval: 5, repeats: false)
    let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: trigger)

    UNUserNotificationCenter.current().add(request) { error in
        if let error = error {
            print("Error: \(error)")
        }
    }
}
