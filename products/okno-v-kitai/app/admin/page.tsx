import { AdminConsole } from "@/components/admin-console";

export default function AdminPage() {
  return (
    <main className="mx-auto w-full max-w-[1560px] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-7 max-w-4xl">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#6f91ff]">Pilot control plane</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-white sm:text-4xl">Администрирование</h1>
        <p className="mt-3 text-sm leading-6 text-zinc-400">
          Состояние интеграций, RBAC, управляемые источники, audit trail и backup/restore runtime-конфигурации. Изменения сохраняются в отдельном volume и не требуют пересборки образа.
        </p>
      </div>
      <AdminConsole />
    </main>
  );
}
