"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { startGpsTracking, stopGpsTracking } from "@/lib/gps";
import { fetchApi } from "@/lib/api";

export default function GpsPage() {
  const t = useTranslations();
  const params = useParams();
  const caseId = params.id as string;
  const [tracking, setTracking] = useState(false);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    fetchApi(`/cases/${caseId}/gps/logs`).then(setLogs).catch(() => {});
  }, [caseId]);

  const toggle = async () => {
    if (tracking) {
      await stopGpsTracking();
      setTracking(false);
    } else {
      await startGpsTracking(caseId);
      setTracking(true);
    }
  };

  return (
    <div className="mx-auto max-w-2xl p-4 space-y-4">
      <h1 className="text-xl font-bold">GPS 위치 추적</h1>

      <button
        onClick={toggle}
        className={`w-full rounded-lg px-4 py-3 font-medium text-white ${
          tracking ? "bg-red-600 hover:bg-red-700" : "bg-green-600 hover:bg-green-700"
        }`}
      >
        {tracking ? "추적 중지" : "추적 시작"}
      </button>

      {tracking && (
        <p className="text-sm text-green-600 text-center animate-pulse">
          📍 위치 수집 중 (백그라운드에서도 동작)
        </p>
      )}

      <div className="mt-6">
        <h2 className="font-medium text-sm text-gray-500 mb-2">
          수집된 로그 ({logs.length}건)
        </h2>
        <div className="max-h-60 overflow-y-auto space-y-1">
          {logs.slice(-20).reverse().map((log: any, i: number) => (
            <div key={i} className="flex justify-between text-xs border-b py-1">
              <span>{log.ts?.slice(11, 19)}</span>
              <span className={log.status === "IN_WORKPLACE" ? "text-green-600" : "text-orange-500"}>
                {log.status || "?"}
              </span>
              <span className="text-gray-400">
                {log.lat?.toFixed(4)}, {log.lng?.toFixed(4)}
              </span>
            </div>
          ))}
        </div>
      </div>

      <p className="text-xs text-gray-400">{t("disclaimer")}</p>
    </div>
  );
}
