import { Link, NavLink } from "react-router-dom";
import { ArrowRight } from "lucide-react";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-1.5 text-sm transition ${isActive ? "bg-card text-ink ring-1 ring-line" : "text-muted hover:text-ink"}`;

export function Logo() {
  return (
    <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-bill text-white">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.6"
        strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
    </span>
  );
}

export default function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-line/70 bg-paper/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5" aria-label="BillBuddy Health home">
          <Logo />
          <span className="hidden font-display text-xl sm:inline">BillBuddy <span className="text-match">Health</span></span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2" aria-label="Main">
          <NavLink to="/" end className={navClass}>Home</NavLink>
          <NavLink to="/about" className={navClass}>About</NavLink>
          <NavLink
            to="/analyze"
            className={({ isActive }) =>
              `ml-1 inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium shadow-sm transition sm:ml-2 ${
                isActive ? "bg-bill text-white" : "bg-ink text-white hover:bg-ink/90"
              }`}
          >
            Check my bill <ArrowRight size={15} aria-hidden />
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
