"use client";

import Link from "next/link";

import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/documents" className="flex items-center gap-2 font-semibold text-slate-800">
          <span className="text-brand-600">📄</span> Document Analysis
        </Link>
        <nav className="flex items-center gap-4 text-sm">
          {user ? (
            <>
              <Link href="/documents" className="text-slate-600 hover:text-slate-900">
                Documents
              </Link>
              <span className="hidden text-slate-400 sm:inline">{user.email}</span>
              <button
                onClick={logout}
                className="rounded-md border border-slate-300 px-3 py-1 text-slate-700 hover:bg-slate-50"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-slate-600 hover:text-slate-900">
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded-md bg-brand-600 px-3 py-1 text-white hover:bg-brand-700"
              >
                Sign up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
