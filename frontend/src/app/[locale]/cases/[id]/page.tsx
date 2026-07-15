"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { fetchApi } from "@/lib/api";
import Link from "next/link";

export default function CaseDetailPage() {
  const t = useTranslations();
  const params = useParams();
  const caseId = params.id as string;
  const [caseData, setCaseData] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);

  useEffect(() => {
    fetchApi(`/cases/${caseId}`).then(setCaseData).catch(() => {});
    fetchApi(`/cases/${caseId}/analysis`).then(setAnalysis).catch(() => {});
  }, [caseId]);

  const runAnalysis = async () => {
    await fetchApi(`/cases/${caseId}/analyze`, { method: "POST", body: "{}" });
    const result = await fetchApi(`/cases/${caseId}/analysis`);
    setAnalysis(result);
  };

  if (!caseData) return <p className="p-4">{t("common.loading")}</p>;

  return (
    <div className="mx-auto max-w-2xl p-4 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">{caseData.workplace_name || caseData.title}</h1>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs">{caseData.status}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><span className="text-gray-500">{t("cases.employer")}:</span> {caseData.employer_name || "-"}</div>
        <div><span className="text-gray-500">{t("cases.wage")}:</span> {caseData.agreed_hourly_wage?.toLocaleString() || "-"}원</div>
        <div><span className="text-gray-500">{t("cases.period")}:</span> {caseData.work_start_date || "?"} ~</div>
      </div>

      <div className="flex gap-2">
        <Link href={`/cases/${caseId}/upload`} className="rounded-lg bg-gray-200 px-4 py-2 text-sm hover:bg-gray-300">
          {t("upload.title")}
        </Link>
        <button onClick={runAnalysis} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700">
          {t("analysis.run")}
        </button>
      </div>

      {analysis && (
        <div className="rounded-lg border bg-white p-4 space-y-3">
          <h2 className="font-bold">{t("analysis.title")}</h2>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded bg-blue-50 p-3">
              <p className="text-xs text-gray-500">{t("analysis.expected")}</p>
              <p className="font-bold">{analysis.wage?.expected?.toLocaleString() || 0}원</p>
            </div>
            <div className="rounded bg-green-50 p-3">
              <p className="text-xs text-gray-500">{t("analysis.received")}</p>
              <p className="font-bold">{analysis.wage?.received?.toLocaleString() || 0}원</p>
            </div>
            <div className="rounded bg-red-50 p-3">
              <p className="text-xs text-gray-500">{t("analysis.suspected")}</p>
              <p className="font-bold text-red-600">{analysis.wage?.suspected_unpaid?.toLocaleString() || 0}원</p>
            </div>
          </div>
        </div>
      )}

      <p className="text-xs text-gray-400">{t("disclaimer")}</p>
    </div>
  );
}
