import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { query, SCHEMA } from "@/lib/db";

export const dynamic = "force-dynamic";

type Row = Record<string, unknown> & { id: number };

async function rows(): Promise<Row[]> {
  try {
    return await query<Row>(`SELECT * FROM "${SCHEMA}"."products" ORDER BY id DESC LIMIT 100`);
  } catch {
    return [];
  }
}

export default async function ProductListPage() {
  const data = await rows();
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Products</h1>
        <Link href="/product/new"><Button>New Product</Button></Link>
      </div>
      <div className="rounded-lg border">
        <Table>
          <THead>
            <TR>
              <TH>ID</TH>
              <TH>name</TH><TH>sku</TH><TH>description</TH><TH>unit_price</TH>
              <TH>Actions</TH>
            </TR>
          </THead>
          <TBody>
            {data.length === 0 ? (
              <TR>
                <TD colSpan={ 6 } className="text-center text-muted-foreground">
                  No Products yet.
                </TD>
              </TR>
            ) : (
              data.map((r) => (
                <TR key={r.id}>
                  <TD className="font-mono text-xs">{r.id}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["name"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["sku"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["description"] ?? "")}</TD>
                  
                  <TD>{String((r as Record<string, unknown>)["unit_price"] ?? "")}</TD>
                  
                  <TD><Link className="underline" href={`/product/${r.id}`}>View</Link></TD>
                </TR>
              ))
            )}
          </TBody>
        </Table>
      </div>
    </div>
  );
}
