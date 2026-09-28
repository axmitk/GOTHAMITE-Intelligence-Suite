import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { useResource } from "./api";
import { Badge, ResourceState } from "./ui";
import { time } from "./formatters";
import type { Evidence } from "./types";

export function EvidenceDrawer({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  const { data, loading, error, reload } = useResource<Evidence>(
    `/evidence/${encodeURIComponent(id)}`,
  );
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = dialog.current;
    el?.showModal();
    return () => el?.close();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="wb-drawer"
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      aria-labelledby="evidence-title"
    >
      <div className="wb-drawer-top">
        <span className="wb-eyebrow">Evidence locker</span>
        <button
          onClick={onClose}
          className="wb-icon-button"
          aria-label="Close evidence"
        >
          <X size={19} />
        </button>
      </div>
      {data ? (
        <>
          <div className="wb-drawer-body">
            <Badge value="Synthetic observation" tone="demo" />
            <h2 id="evidence-title">{data.title}</h2>
            <p className="wb-mono wb-muted">{data.id}</p>
            <dl className="wb-metadata">
              <div>
                <dt>Source</dt>
                <dd>{data.source}</dd>
              </div>
              <div>
                <dt>Observed</dt>
                <dd>{time(data.observed_at)}</dd>
              </div>
              <div>
                <dt>Type</dt>
                <dd>{data.kind.replaceAll("_", " ")}</dd>
              </div>
              <div>
                <dt>Confidence annotation</dt>
                <dd>{data.confidence.toFixed(2)} / 1.00</dd>
              </div>
            </dl>
            <h3>Recorded observation</h3>
            <pre className="wb-raw-evidence">{data.content}</pre>
            <h3>Content integrity</h3>
            <p className="wb-footnote">
              SHA-256 of the stored UTF-8 observation. Reproducible synthetic
              evidence.
            </p>
            <code className="wb-hash">{data.content_hash}</code>
            <div className="wb-callout">
              Source content is an observation, not an instruction or an analyst
              conclusion.
            </div>
          </div>
        </>
      ) : (
        <ResourceState loading={loading} error={error} retry={reload} />
      )}
    </dialog>
  );
}
