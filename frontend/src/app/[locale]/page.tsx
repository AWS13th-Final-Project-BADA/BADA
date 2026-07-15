"use client";

import { useTranslations } from "next-intl";
import { useEffect } from "react";
import { handleAuthCallback, isLoggedIn, loginWithCognito, loginWithProvider } from "@/lib/auth";
import { useRouter } from "next/navigation";

export default function Home() {
  const t = useTranslations();
  const router = useRouter();

  useEffect(() => {
    handleAuthCallback();
    if (isLoggedIn()) router.replace("/cases");
  }, [router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6">
      <div className="w-full max-w-sm space-y-6 text-center">
        <h1 className="text-3xl font-bold text-indigo-700">{t("common.appName")}</h1>
        <p className="text-gray-600">{t("common.tagline")}</p>

        <div className="space-y-3 pt-4">
          <button
            onClick={loginWithCognito}
            className="w-full rounded-lg bg-indigo-600 px-4 py-3 text-white font-medium hover:bg-indigo-700"
          >
            {t("common.login")}
          </button>
          <button
            onClick={() => loginWithProvider("kakao")}
            className="w-full rounded-lg bg-yellow-400 px-4 py-3 text-gray-900 font-medium hover:bg-yellow-500"
          >
            카카오로 로그인
          </button>
          <button
            onClick={() => loginWithProvider("google")}
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-700 font-medium hover:bg-gray-50"
          >
            Google로 로그인
          </button>
        </div>

        <p className="text-xs text-gray-400 pt-6">{t("disclaimer")}</p>
      </div>
    </main>
  );
}
