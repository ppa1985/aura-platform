import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

async function getCounts() {
  const counts: Record<string, number> = {};
  
  try {
    const r = await query<{ count: string }>(`SELECT COUNT(*)::text AS count FROM "app_warehouse_management_system"."warehouses"`);
    counts["Warehouse"] = Number(r[0]?.count ?? 0);
  } catch {
    counts["Warehouse"] = 0;
  }
  
  try {
    const r = await query<{ count: string }>(`SELECT COUNT(*)::text AS count FROM "app_warehouse_management_system"."products"`);
    counts["Product"] = Number(r[0]?.count ?? 0);
  } catch {
    counts["Product"] = 0;
  }
  
  try {
    const r = await query<{ count: string }>(`SELECT COUNT(*)::text AS count FROM "app_warehouse_management_system"."inventory_levels"`);
    counts["InventoryLevel"] = Number(r[0]?.count ?? 0);
  } catch {
    counts["InventoryLevel"] = 0;
  }
  
  try {
    const r = await query<{ count: string }>(`SELECT COUNT(*)::text AS count FROM "app_warehouse_management_system"."shipments"`);
    counts["Shipment"] = Number(r[0]?.count ?? 0);
  } catch {
    counts["Shipment"] = 0;
  }
  
  try {
    const r = await query<{ count: string }>(`SELECT COUNT(*)::text AS count FROM "app_warehouse_management_system"."suppliers"`);
    counts["Supplier"] = Number(r[0]?.count ?? 0);
  } catch {
    counts["Supplier"] = 0;
  }
  
  return counts;
}

export default async function Dashboard() {
  const counts = await getCounts();
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Warehouse Management System</h1>
        <p className="text-muted-foreground">Build me a Warehouse Management System with products, warehouses, inventory levels, and inbound/outbound shipments.</p>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        
        <Card>
          <CardHeader><CardTitle>Warehouses</CardTitle></CardHeader>
          <CardContent>
            <div className="text-4xl font-semibold">{counts["Warehouse"] ?? 0}</div>
            <a href="/warehouse" className="text-sm text-muted-foreground hover:underline">View all →</a>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader><CardTitle>Products</CardTitle></CardHeader>
          <CardContent>
            <div className="text-4xl font-semibold">{counts["Product"] ?? 0}</div>
            <a href="/product" className="text-sm text-muted-foreground hover:underline">View all →</a>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader><CardTitle>InventoryLevels</CardTitle></CardHeader>
          <CardContent>
            <div className="text-4xl font-semibold">{counts["InventoryLevel"] ?? 0}</div>
            <a href="/inventory-level" className="text-sm text-muted-foreground hover:underline">View all →</a>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader><CardTitle>Shipments</CardTitle></CardHeader>
          <CardContent>
            <div className="text-4xl font-semibold">{counts["Shipment"] ?? 0}</div>
            <a href="/shipment" className="text-sm text-muted-foreground hover:underline">View all →</a>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader><CardTitle>Suppliers</CardTitle></CardHeader>
          <CardContent>
            <div className="text-4xl font-semibold">{counts["Supplier"] ?? 0}</div>
            <a href="/supplier" className="text-sm text-muted-foreground hover:underline">View all →</a>
          </CardContent>
        </Card>
        
      </div>
    </div>
  );
}
