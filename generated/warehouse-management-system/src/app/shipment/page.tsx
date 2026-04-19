import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { query, SCHEMA } from "@/lib/db";

export const dynamic = "force-dynamic";

type Row = Record<string, unknown> & { id: number };

async function rows(): Promise<Row[]> {
  try {
    return await query<Row>(`SELECT * FROM "${SCHEMA}"."shipments" ORDER BY id DESC LIMIT 100`);
  } catch {
    return [];
  }
}

export default async function ShipmentListPage() {
  const data = await rows();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Shipments</h1>
        <Link href="/shipment/new"><Button>New Shipment</Button></Link>
      </div>
      <div className="rounded-lg border">
        <Table>
          <THead>
            <TR>
              <TH>ID</TH>
              <TH>reference</TH><TH>direction</TH><TH>status</TH><TH>shipped_at</TH>
              <TH>Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.length === 0 ? (
              <TR>
                <TD colSpan={ 6 } className="text-center text-muted-foreground">
                  No Shipments yet.
                </TD>
              </TR>
            ) : (
              data.map((r) => (
                <TR key={r.id}>
                  <TD className="font-mono text-xs">{r.id}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["reference"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["direction"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["status"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["shipped_at"] ?? "")}</TD>
                  
                  <TD><Link className="underline" href={`/shipment/${r.id}`}>View</Link></TD>
                </TR>
              ))
            )}
          </TBody>
        </Table>
      </div>
    </div>
  );
}
