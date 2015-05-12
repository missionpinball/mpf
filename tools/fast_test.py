import fastpinball

ports = [('\\.\COM10', 921600), ('\\.\COM11', 921600), ('\\.\COM12', 921600)]  # dmd, net, led
portAssignments = (1, 0, 2)

dev = fastpinball.fpOpen(ports, portAssignments)
fastpinball.fpTimerConfig(dev, 100000)
fast_events = fastpinball.fpGetEventObject()

tick = 0

while True:
    fastpinball.fpEventPoll(dev, fast_events)
    event = fastpinball.fpGetEventType(fast_events)

    print event

    if event == fastpinball.FP_EVENT_TYPE_TIMER_TICK:
        tick += 1
        print tick
