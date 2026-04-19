import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { query, SCHEMA } from "@/lib/db";

export const dynamic = "force-dynamic";

type Row = Record<string, unknown> & { id: number };

async function rows(): Promise<Row[]> {
  try {
    return await query<Row>(`SELECT * FROM "${SCHEMA}"."inventory_levels" ORDER BY id DESC LIMIT 100`);
  } catch {
    return [];
  }
}

export default async function InventoryLevelListPage() {
  const data = await rows();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">InventoryLevels</h1>
        <Link href="/inventory-level/new"><Button>New InventoryLevel</Button></Link>
      </div>
      <div className="rounded-lg border">
        <Table>
          <THead>
            <TR>
              <TH>ID</TH>
              <TH>quantity</TH><TH>min_quantity</TH><TH>reorder_point</TH>
              <TH>Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.length === 0 ? (
              <TR>
                <TD colSpan={ 5 } className="text-center text-muted-foreground">
                  No InventoryLevels yet.
                </TD>
              </TR>
            ) : (
              data.map((r) => (
                <TR key={r.id}>
                  <TD className="font-mono text-xs">{r.id}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["quantity"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["min_quantity"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["reorder_point"] ?? "")}</TD>
                  
                  <TD><Link className="underline" href={`/inventory-level/${r.id}`}>View</Link></TD>
                </TR>
              ))
            )}
          </TBody>
        </Table>
      </div>
    </div>
  );
}
