"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";
import Link from "next/link";

interface Case {
  id: string;
  title: string;
  workplace_name: string | null;
  status: string;
  created_at: string;
}

export default function CasesPage() {
  const t = useTranslations("cases");
  const [cases, setCases] = useState<Case[]>([]);

  useEffect(() => {
    fetchApi<Case[]>("/cases").then(setCases).catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-2xl p-4">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold">{t("title")}</h1>
        <Link
          href="/cases/new"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700"
        >
          {t("create")}
        </Link>
      </div>

      <div className="space-y-3">
        {cases.map((c) => (
          <Link
            key={c.id}
            href={`/cases/${c.id}`}
            className="block rounded-lg border bg-white p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex justify-between items-center">
              <div>
                <p className="font-medium">{c.workplace_name || c.title}</p>
                <p className="text-sm text-gray-500">{c.created_at?.slice(0, 10)}</p>
              </div>
              <span className="rounded-full bg-gray-100 px-3 py-1 text-xs">{c.status}</span>
            </div>
          </Link>
        ))}
        {cases.length === 0 && (
          <p className="text-center text-gray-400 py-12">아직 사건이 없습니다.</p>
        )}
      </div>
    </div>
  );
}
