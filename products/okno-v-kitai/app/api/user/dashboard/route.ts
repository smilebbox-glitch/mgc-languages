import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { getSubscriptions, getTrip, listFavorites, listNotifications } from "@/lib/user-store";
import { resolveUserContext, withUserCookie } from "@/lib/user-context";
export const dynamic="force-dynamic";
export async function GET(request:Request){const c=createRequestContext(request),u=resolveUserContext(request);const preferences=getSubscriptions(u.userKey),favorites=listFavorites(u.userKey),trip=getTrip(u.userKey),notifications=listNotifications(u.userKey,50);return jsonWithContext(c,{preferences,favorites,trip,notifications,unread:notifications.filter(n=>!n.readAt).length,identity:{authenticated:u.authenticated}},{headers:withUserCookie(u,{"cache-control":"no-store"})});}
