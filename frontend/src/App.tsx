import { useEffect } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";
import SiteHeader from "./components/SiteHeader";
import HomePage from "./pages/HomePage";
import AboutPage from "./pages/AboutPage";
import AnalyzePage from "./pages/AnalyzePage";

/** Scroll to the top when moving between pages (but not for #anchors on the same page). */
function ScrollToTop() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) window.scrollTo({ top: 0 });
  }, [pathname, hash]);
  return null;
}

function NotFound() {
  return (
    <div className="mx-auto max-w-md py-20 text-center">
      <p className="font-display text-3xl">Page not found</p>
      <Link to="/" className="mt-4 inline-block text-match underline underline-offset-4">Back to home</Link>
    </div>
  );
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <ScrollToTop />
      <SiteHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/analyze" element={<AnalyzePage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
      <footer className="mx-auto w-full max-w-6xl px-4 pb-10 text-xs text-muted sm:px-6">
        BillBuddy Health helps you prepare questions; it does not provide medical, legal, or financial advice and
        can't confirm billing errors. Always verify with your provider and insurer. Built at HackRU Fall 2026.
      </footer>
    </div>
  );
}
