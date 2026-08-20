export function formatEpsilon(value: number) {
  return Number(value.toPrecision(12)).toString();
}
