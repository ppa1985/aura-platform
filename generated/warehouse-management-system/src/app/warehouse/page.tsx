import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { query, SCHEMA } from "@/lib/db";

export const dynamic = "force-dynamic";

type Row = Record<string, unknown> & { id: number };

async function rows(): Promise<Row[]> {
  try {
    return await query<Row>(`SELECT * FROM "${SCHEMA}"."warehouses" ORDER BY id DESC LIMIT 100`);
  } catch {
    return [];
  }
}

export default async function WarehouseListPage() {
  const data = await rows();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Warehouses</h1>
        <Link href="/warehouse/new"><Button>New Warehouse</Button></Link>
      </div>
      <div className="rounded-lg border">
        <Table>
          <THead>
            <TR>
              <TH>ID</TH>
              <TH>name</TH><TH>code</TH><TH>address</TH>
              <TH>Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.length === 0 ? (
              <TR>
                <TD colSpan={ 5 } className="text-center text-muted-foreground">
                  No Warehouses yet.
                </TD>
              </TR>
            ) : (
              data.map((r) => (
                <TR key={r.id}>
                  <TD className="font-mono text-xs">{r.id}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["name"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["code"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["address"] ?? "")}</TD>
                  
                  <TD><Link className="underline" href={`/warehouse/${r.id}`}>View</Link></TD>
                </TR>
              ))
            )}
          </TBody>
        </Table>
      </div>
    </div>
  );
}
