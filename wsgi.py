# wsgi.py — debug import helper (قرار بده در ریشه پروژه)
import importlib, traceback, sys

print(">>> STARTING DEBUG wsgi.py")

try:
    # تلاش برای import ماژول app
    mod = importlib.import_module("app")
    print(">>> imported module 'app' ->", mod)
    # چاپ لیست attribute ها تا معلوم شود چه اسمی وجود دارد
    attrs = dir(mod)
    print(">>> dir(app):", attrs)

    # سعی میکنیم یک شیء WSGI پیدا کنیم از بین نام‌های معمول
    app_obj = None
    for candidate in ("app", "server", "application", "flask_app"):
        if candidate in attrs:
            app_obj = getattr(mod, candidate)
            print(f">>> found candidate '{candidate}' ->", app_obj)
            break

    if app_obj is None:
        print(">>> No WSGI app found in module 'app' (checked app, server, application, flask_app).")
        # برای شفاف‌تر شدن خطا، پرینت مقدارهای مهم
        try:
            import inspect
            print(">>> module file:", getattr(mod, "__file__", None))
            print(">>> module doc:", getattr(mod, "__doc__", None))
            if hasattr(mod, "__dict__"):
                keys = [k for k in mod.__dict__.keys() if not k.startswith("__")]
                print(">>> top-level keys:", keys)
        except Exception:
            pass
        raise RuntimeError("No WSGI app attribute found in module 'app'.")

    # اگر پیدا شد — server را ست کن
    server = app_obj
    print(">>> DEBUG: server set to:", server)

except Exception:
    print(">>> EXCEPTION during import:")
    traceback.print_exc()
    # نذاریم silent رد بشه — مجدداً بالا بیاندازیم تا Gunicorn لاگ کند
    raise
