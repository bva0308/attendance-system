import gc
gc.enable()

try:
    import esp
    esp.osdebug(None)
except Exception:
    pass
