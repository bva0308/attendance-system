const liveEndpoints = new Set([
  "students.dashboard_home",
  "attendance.attendance_records",
  "students.devices_page",
]);

const currentEndpoint = document.body.dataset.endpoint || "";
if (liveEndpoints.has(currentEndpoint)) {
  setInterval(() => {
    if (document.hidden) {
      return;
    }
    const activeTag = document.activeElement ? document.activeElement.tagName : "";
    if (activeTag === "INPUT" || activeTag === "SELECT" || activeTag === "TEXTAREA") {
      return;
    }
    window.location.reload();
  }, 5000);
}
