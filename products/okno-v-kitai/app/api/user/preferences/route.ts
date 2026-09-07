import { checkRateLimit, rateLimitHeaders } from "@/lib/rate-limit";
import { createRequestContext, jsonWithContext } from "@/lib/request-context";
import { getSubscriptions, saveSubscriptions } from "@/lib/user-store";
import { resolveUserContext, withUserCookie } from "@/lib/user-context";
export const dynamic="force-dynamic";
export async function GET(request:Request){const c=createRequestContext(request),u=resolveUserContext(request),l=checkRateLimit({context:c,scope:"user-pref-read",limit:120,actor:u.userKey});if(!l.allowed)return jsonWithContext(c,{error:"Слишком много запросов."},{status:429,headers:rateLimitHeaders(l)});return jsonWithContext(c,getSubscriptions(u.userKey),{headers:withUserCookie(u,{"cache-control":"no-store",...rateLimitHeaders(l)})});}
export async function PUT(request:Request){const c=createRequestContext(request),u=resolveUserContext(request),l=checkRateLimit({context:c,scope:"user-pref-write",limit:30,actor:u.userKey});if(!l.allowed)return jsonWithContext(c,{error:"Слишком много запросов."},{status:429,headers:rateLimitHeaders(l)});const body=await request.json().catch(()=>({}));return jsonWithContext(c,saveSubscriptions(u.userKey,body),{headers:withUserCookie(u,{"cache-control":"no-store",...rateLimitHeaders(l)})});}
