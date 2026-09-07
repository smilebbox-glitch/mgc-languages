import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { trackUsage } from "@/lib/user-store";
import { resolveUserContext, withUserCookie } from "@/lib/user-context";
export const dynamic="force-dynamic";
export async function POST(request:Request){const c=createRequestContext(request),u=resolveUserContext(request),body=await request.json().catch(()=>({}));const eventName=typeof body.eventName==="string"?body.eventName:"unknown",path=typeof body.path==="string"?body.path:new URL(request.url).pathname,metadata=body.metadata&&typeof body.metadata==="object"?body.metadata:{};trackUsage(u.userKey,eventName,path,metadata);return jsonWithContext(c,{ok:true},{headers:withUserCookie(u,{"cache-control":"no-store"})});}
