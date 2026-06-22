"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { fetchApi } from "@/lib/api";

export default function NewCasePage() {
  const t = useTranslations("cases");
  const router = useRouter();
  const [form, setForm] = useState({
    workplace_name: "",
    employer_name: "",
    work_start_date: "",
    agreed_hourly_wage: "",
    issue_types: ["wage_unpaid"],
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...form,
      agreed_hourly_wage: form.agreed_hourly_wage ? Number(form.agreed_hourly_wage) : null,
    };
    const created = await fetchApi("/cases", { method: "POST", body: JSON.stringify(payload) });
    router.push(`/cases/${created.id}`);
  };

  return (
    <div className="mx-auto max-w-md p-4">
      <h1 className="text-xl font-bold mb-6">{t("create")}</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-sm font-medium">{t("workplace")}</label>
          <input type="text" required className="mt-1 block w-full rounded-lg border-gray-300"
            value={form.workplace_name} onChange={(e) => setForm({ ...form, workplace_name: e.target.value })} />
        </div>
        <div>
          <label className="text-sm font-medium">{t("employer")}</label>
          <input type="text" className="mt-1 block w-full rounded-lg border-gray-300"
            value={form.employer_name} onChange={(e) => setForm({ ...form, employer_name: e.target.value })} />
        </div>
        <div>
          <label className="text-sm font-medium">{t("period")} (시작일)</label>
          <input type="date" className="mt-1 block w-full rounded-lg border-gray-300"
            value={form.work_start_date} onChange={(e) => setForm({ ...form, work_start_date: e.target.value })} />
        </div>
        <div>
          <label className="text-sm font-medium">{t("wage")} (원)</label>
          <input type="number" className="mt-1 block w-full rounded-lg border-gray-300" placeholder="9860"
            value={form.agreed_hourly_wage} onChange={(e) => setForm({ ...form, agreed_hourly_wage: e.target.value })} />
        </div>
        <button type="submit" className="w-full rounded-lg bg-indigo-600 px-4 py-3 text-white font-medium hover:bg-indigo-700">
          {t("create")}
        </button>
      </form>
    </div>
  );
}
