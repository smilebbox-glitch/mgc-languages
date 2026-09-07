import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { getTrip, saveTrip, trackUsage } from "@/lib/user-store";
import { resolveUserContext, withUserCookie } from "@/lib/user-context";
export const dynamic="force-dynamic";
export async function GET(request:Request){const c=createRequestContext(request),u=resolveUserContext(request);return jsonWithContext(c,{trip:getTrip(u.userKey)},{headers:withUserCookie(u,{"cache-control":"no-store"})});}
export async function PUT(request:Request){const c=createRequestContext(request),u=resolveUserContext(request),body=await request.json().catch(()=>({}));const trip=saveTrip(u.userKey,body);trackUsage(u.userKey,"trip_save",new URL(request.url).pathname,{city:trip.city,eventId:trip.eventId});return jsonWithContext(c,{trip},{headers:withUserCookie(u,{"cache-control":"no-store"})});}
