const dates = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC'
});
const numbers = new Intl.NumberFormat('en-GB');

/** 2016-11-24 or a Wayback 20161124093000 stamp, as 24 Nov 2016 */
export function date(day: string) {
  const digits = day.replaceAll('-', '');
  return dates.format(Date.UTC(+digits.slice(0, 4), +digits.slice(4, 6) - 1, +digits.slice(6, 8)));
}

export const count = (n: number) => numbers.format(n);

/** A share as "3 in 10", which reads easier than 30.4% */
export const inTen = (part: number, whole: number) => `${Math.round((part / whole) * 10)} in 10`;

export const percent = (part: number, whole: number) =>
  `${whole ? Math.round((part / whole) * 100) : 0}%`;

export function plural(n: number, one: string, many = `${one}s`) {
  return `${count(n)} ${n === 1 ? one : many}`;
}

/** The same day a few years back, with 29 Feb landing on the 28th */
export function yearsBefore(day: string, years: number) {
  const [year, month, dayOfMonth] = day.split('-').map(Number);
  const then = new Date(Date.UTC(year - years, month - 1, dayOfMonth));
  if (then.getUTCMonth() !== month - 1) then.setUTCDate(0);
  return then.toISOString().slice(0, 10);
}

export function today() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}
