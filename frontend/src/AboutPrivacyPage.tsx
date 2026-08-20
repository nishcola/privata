import { PageHeader } from "./AppShell";

export default function AboutPrivacyPage() {
  return (
    <>
      <PageHeader title="About Privacy">Privata demonstrates differential privacy under documented assumptions. It does not provide a general privacy or security guarantee.</PageHeader>
      <div className="info-grid">
        <section className="card"><h2>Privacy model</h2><p>One row is one privacy unit. The query service uses fixed-size replacement adjacency: neighboring datasets have the same number of rows and differ in at most one row.</p></section>
        <section className="card"><h2>Public configuration</h2><p>Schemas, numeric bounds, categorical domains, histogram edges, dataset size, and session/query epsilon are treated as public. Bounds are not inferred from records.</p></section>
        <section className="card"><h2>Releases and budget</h2><p>Supported releases use the Laplace mechanism. Sessions use simple sequential composition, and a request is rejected before execution when it would exceed the remaining budget.</p></section>
        <section className="card"><h2>Strict and demo modes</h2><p>Strict mode never returns ground truth. Demo ground truth is intentionally non-private and appears only for a dataset explicitly marked safe for demonstration.</p></section>
      </div>
      <section className="card"><h2>Scope boundaries</h2><p>Privata does not address malicious server operators, compromised hosts, side channels, multi-row contributions per person, linkage attacks outside the release model, encrypted storage, access control, or distributed production accounting.</p></section>
    </>
  );
}
