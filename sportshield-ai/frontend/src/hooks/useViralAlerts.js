import { useState, useEffect, useRef } from "react";
import { rtdb, ref, onValue, off } from "../lib/firebase";

export function useViralAlerts() {
  const [currentAlert, setCurrentAlert] = useState(null);
  const [allAlerts, setAllAlerts] = useState([]);
  const lastAlertIdRef = useRef(null);

  useEffect(() => {
    if (window.Notification && Notification.permission !== "granted") {
      Notification.requestPermission();
    }

    const alertsRef = ref(rtdb, "viral_alerts");
    const unsubscribe = onValue(alertsRef, (snapshot) => {
      if (snapshot.exists()) {
        const data = snapshot.val();
        const active = Object.keys(data)
          .map((k) => ({ id: k, ...data[k] }))
          .filter((a) => a.is_active);

        setAllAlerts(active);

        if (active.length > 0) {
          const priority = { VIRAL_SPREAD: 3, RAPID_SPREAD: 2, SPREADING: 1 };
          active.sort(
            (a, b) =>
              (priority[b.alert_level] || 0) - (priority[a.alert_level] || 0),
          );
          const topAlert = active[0];
          setCurrentAlert(topAlert);

          if (
            window.Notification &&
            Notification.permission === "granted" &&
            lastAlertIdRef.current !== topAlert.id
          ) {
            new Notification("SportShield AI Alert", {
              body: `⚠️ ${topAlert.alert_level.replace("_", " ")} DETECTED: ${topAlert.asset_name}`,
            });
            lastAlertIdRef.current = topAlert.id;
          }
        } else {
          setCurrentAlert(null);
        }
      } else {
        setAllAlerts([]);
        setCurrentAlert(null);
      }
    });
    return () => off(alertsRef, "value", unsubscribe);
  }, []);

  return { currentAlert, allAlerts };
}
