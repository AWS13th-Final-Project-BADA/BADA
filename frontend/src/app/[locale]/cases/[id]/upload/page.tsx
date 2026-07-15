"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://api.badasoft.com";

const CATEGORIES = ["contract", "schedule", "payment", "chat", "statement", "other"] as const;

export default function UploadPage() {
  const t = useTranslations("upload");
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;
  const [category, setCategory] = useState<string>("other");
  const [uploading, setUploading] = useState(false);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("category", category);

    const token = localStorage.getItem("access_token");
    await fetch(`${API_BASE}/cases/${caseId}/evidences/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    setUploading(false);
    router.push(`/cases/${caseId}`);
  };

  return (
    <div className="mx-auto max-w-md p-4 space-y-6">
      <h1 className="text-xl font-bold">{t("title")}</h1>

      <div>
        <label className="text-sm font-medium text-gray-700">{t("category")}</label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="mt-1 block w-full rounded-lg border-gray-300"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{t(`categories.${c}`)}</option>
          ))}
        </select>
      </div>

      <label className="flex flex-col items-center justify-center h-40 rounded-lg border-2 border-dashed border-gray-300 cursor-pointer hover:border-indigo-400 transition-colors">
        <p className="text-sm text-gray-500">{uploading ? "업로드 중..." : t("dropzone")}</p>
        <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
      </label>
    </div>
  );
}
