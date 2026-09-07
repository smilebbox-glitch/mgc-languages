import { authorize } from "@/lib/auth";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { usageSummary } from "@/lib/user-store";
export const dynamic="force-dynamic";
export async function GET(request:Request){const c=createRequestContext(request),auth=authorize(request,"admin",c.requestId);if(auth.response)return auth.response;const days=Number(new URL(request.url).searchParams.get("days")||30);return jsonWithContext(c,usageSummary(days),{headers:{"cache-control":"no-store"}});}
