import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { generateUserNotifications, listNotifications, markNotificationsRead } from "@/lib/user-store";
import { resolveUserContext, withUserCookie } from "@/lib/user-context";
export const dynamic="force-dynamic";
export async function GET(request:Request){const c=createRequestContext(request),u=resolveUserContext(request);generateUserNotifications();const notifications=listNotifications(u.userKey);return jsonWithContext(c,{notifications,unread:notifications.filter(n=>!n.readAt).length},{headers:withUserCookie(u,{"cache-control":"no-store"})});}
export async function PATCH(request:Request){const c=createRequestContext(request),u=resolveUserContext(request),body=await request.json().catch(()=>({}));const ids=Array.isArray(body.ids)?body.ids.filter((x:unknown):x is string=>typeof x==="string"):undefined;return jsonWithContext(c,{changed:markNotificationsRead(u.userKey,ids)},{headers:withUserCookie(u,{"cache-control":"no-store"})});}
