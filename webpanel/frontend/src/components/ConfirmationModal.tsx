import { useState } from "react";

interface ConfirmationModalProps {
  title: string;
  message: string;
  riskLevel?: "low" | "medium" | "high" | "critical";
  requiredPhrase?: string;
  confirmLabel?: string;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmationModal({
  title,
  message,
  riskLevel = "medium",
  requiredPhrase,
  confirmLabel = "Confirm",
  onCancel,
  onConfirm,
}: ConfirmationModalProps) {
  const [phrase, setPhrase] = useState("");
  const canConfirm = requiredPhrase ? phrase === requiredPhrase : true;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="confirm-modal" role="dialog" aria-modal="true" aria-label={title}>
        <span className={`risk-pill ${riskLevel}`}>{riskLevel}</span>
        <h2>{title}</h2>
        <p>{message}</p>
        {requiredPhrase ? (
          <label>
            <span>Type {requiredPhrase}</span>
            <input onChange={(event) => setPhrase(event.target.value)} value={phrase} />
          </label>
        ) : null}
        <div className="modal-actions">
          <button className="icon-text-button" onClick={onCancel} type="button">
            Cancel
          </button>
          <button className="primary-button compact" disabled={!canConfirm} onClick={onConfirm} type="button">
            {confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
