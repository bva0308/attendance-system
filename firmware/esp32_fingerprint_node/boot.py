try:
    import main

    main.main()
except Exception as exc:
    print("[boot] fingerprint node crashed:", exc)
