import { useMeta } from "@/context/AuthContext";
import { PageHead } from "@/components/Common";

export function Frame({ screen, children, actions, sub }) {
  const m = useMeta();
  return (
    <div data-testid={`screen-${screen.id}`}>
      <PageHead eyebrow={`${screen.role === "shared" ? "Shared access" : m.roleInfo?.name} · ${screen.id}`} title={screen.title} sub={sub || `${screen.workflow} · ${screen.fr}`}>{actions}</PageHead>
      {children}
    </div>
  );
}

export function MFrame({ screen, children, greeting, sub }) {
  return (
    <div data-testid={`screen-${screen.id}`}>
      <div className="ce-mobile-header" style={{ paddingTop: 0 }}>
        {greeting && <div className="text-[13px] text-[#c9d6ea]">{greeting}</div>}
        <h1 className="text-[23px] font-bold text-white tracking-tight mt-1" data-testid="page-title">{screen.title}</h1>
        <div className="text-[12px] text-[#a5b7d1] mt-1">{sub || `${screen.id} · ${screen.workflow}`}</div>
      </div>
      <div className="ce-mobile-content">{children}</div>
    </div>
  );
}
