class Pins:
    PWDN_GPIO_NUM = 32
    RESET_GPIO_NUM = None
    XCLK_GPIO_NUM = 0
    SIOD_GPIO_NUM = 26
    SIOC_GPIO_NUM = 27

    Y9_GPIO_NUM = 35
    Y8_GPIO_NUM = 34
    Y7_GPIO_NUM = 39
    Y6_GPIO_NUM = 36
    Y5_GPIO_NUM = 21
    Y4_GPIO_NUM = 19
    Y3_GPIO_NUM = 18
    Y2_GPIO_NUM = 5
    VSYNC_GPIO_NUM = 25
    HREF_GPIO_NUM = 23
    PCLK_GPIO_NUM = 22

    # Sensor wiring:
    # R307 TX -> ESP32 RX2 (GPIO16)
    # R307 RX -> ESP32 TX2 (GPIO17)
    R307_UART_RX_PIN = 16
    R307_UART_TX_PIN = 17
    # Legacy aliases kept so older notes/scripts do not break.
    R307_RX_PIN = R307_UART_TX_PIN
    R307_TX_PIN = R307_UART_RX_PIN
    RELAY_PIN = 13
    STATUS_LED_PIN = 33
