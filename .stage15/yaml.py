def safe_load(source):
    jobs = {}
    in_jobs = False
    current_job = None
    for raw_line in source.splitlines():
        stripped = raw_line.strip()
        indent = len(raw_line) - len(raw_line.lstrip())
        if not in_jobs:
            if indent == 0 and stripped == "jobs:":
                in_jobs = True
            continue
        if stripped and indent == 0:
            break
        if indent == 2 and stripped.endswith(":"):
            current_job = stripped[:-1]
            jobs[current_job] = {}
        elif (
            current_job
            and indent == 4
            and stripped.startswith("timeout-minutes:")
        ):
            value = stripped.split(":", 1)[1].strip()
            jobs[current_job]["timeout-minutes"] = (
                int(value) if value.isdigit() else value
            )
    return {"jobs": jobs}
