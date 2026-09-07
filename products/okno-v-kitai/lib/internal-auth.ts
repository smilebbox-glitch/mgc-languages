import { timingSafeEqual } from "node:crypto";

function secureEqual(left: string, right: string) {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

export function isSchedulerRequest(request: Request) {
  const expected = process.env.SCHEDULER_TOKEN?.trim() || "";
  const actual = request.headers.get("x-scheduler-token")?.trim() || "";
  return Boolean(expected && actual && secureEqual(expected, actual));
}
