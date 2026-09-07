"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";
export function UsageBeacon(){const path=usePathname();useEffect(()=>{if(!path)return;const body=JSON.stringify({eventName:"page_view",path});if(navigator.sendBeacon){navigator.sendBeacon("/api/user/track",new Blob([body],{type:"application/json"}));}else{void fetch("/api/user/track",{method:"POST",headers:{"content-type":"application/json"},body,keepalive:true});}},[path]);return null;}
