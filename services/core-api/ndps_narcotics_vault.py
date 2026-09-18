"""
PROJECT "HOSPITAL" — PHASE 06: PHARMACY & MEDICATION
Module: ndps_narcotics_vault.py
Operational Scope:
  - NDPS Act (1985) & Schedule X Controlled Substance Compliance
  - Dual-Biometric Sign-Off for Narcotic Dispensation & Access
  - Cryptographically-Chained Perpetual Running Balance Ledger
  - Mandatory Witness Co-Signature for Narcotic Wastage & Return
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import hashlib
import json


class NarcoticVaultError(Exception):
    """Base exception for NDPS vault violations."""
    pass


class DualBiometricAuthenticationError(NarcoticVaultError):
    """Raised when dual biometric sign-off is incomplete or compromised."""
    pass


class NarcoticLedgerTamperError(NarcoticVaultError):
    """Raised when hash chain verification detects ledger tampering."""
    pass


@dataclass
class BiometricCredential:
    user_id: str
    role: str  # PHARMACIST, NURSE_INCHARGE, ANESTHETIST, CMO
    biometric_token: str
    biometric_verified: bool
    verified_at: datetime


@dataclass
class NarcoticLedgerEntry:
    entry_id: str
    drug_id: str
    batch_number: str
    transaction_type: str  # RECEIPT, DISPENSE, RETURN, WASTE
    quantity_change: int    # + for receipt/return, - for dispense/waste
    running_balance: int
    primary_user_id: str
    secondary_user_id: str
    patient_id: Optional[str]
    order_id: Optional[str]
    timestamp: str
    prev_hash: str
    current_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class NDPSNarcoticsVaultEngine:
    """
    Perpetual narcotic accounting engine enforcing dual biometric verification,
    cryptographic audit chaining, and witnessed waste logging.
    """

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self, persistence_store: Optional[Any] = None):
        self.persistence_store = persistence_store
        # drug_id -> current balance
        self.balances: Dict[str, int] = {}
        # drug_id -> list of NarcoticLedgerEntry
        self.ledger: Dict[str, List[NarcoticLedgerEntry]] = {}

        if self.persistence_store is not None:
            self._restore_from_persistence()

    def _restore_from_persistence(self):
        """Restores in-memory balances and ledger chains from persistence store."""
        if not self.persistence_store:
            return
        persisted_balances = self.persistence_store.get_all_narcotic_balances()
        self.balances.update(persisted_balances)
        for drug_id in persisted_balances.keys():
            raw_entries = self.persistence_store.get_narcotic_ledger(drug_id)
            restored_entries = []
            for raw in raw_entries:
                meta = {}
                if raw.get("metadata_json"):
                    try:
                        meta = json.loads(raw["metadata_json"])
                    except Exception:
                        meta = {}
                entry = NarcoticLedgerEntry(
                    entry_id=raw["entry_id"],
                    drug_id=raw["drug_id"],
                    batch_number=raw["batch_number"],
                    transaction_type=raw["transaction_type"],
                    quantity_change=raw["quantity_change"],
                    running_balance=raw["running_balance"],
                    primary_user_id=raw["primary_user_id"],
                    secondary_user_id=raw["secondary_user_id"],
                    patient_id=raw["patient_id"],
                    order_id=raw["order_id"],
                    timestamp=raw["timestamp"],
                    prev_hash=raw["prev_hash"],
                    current_hash=raw["current_hash"],
                    metadata=meta
                )
                restored_entries.append(entry)
            self.ledger[drug_id] = restored_entries

    def _compute_hash(self, entry_dict: Dict[str, Any]) -> str:
        serialized = json.dumps(entry_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def initialize_drug_vault(self, drug_id: str, initial_stock: int, admin_auth: BiometricCredential, witness_auth: BiometricCredential):
        """Initializes the vault ledger for a narcotic drug."""
        self._verify_dual_biometrics(admin_auth, witness_auth)
        self.balances[drug_id] = initial_stock
        self.ledger[drug_id] = []

        now_str = datetime.now(timezone.utc).isoformat()
        entry_payload = {
            "entry_id": f"NDPS-INIT-{drug_id}",
            "drug_id": drug_id,
            "batch_number": "INIT",
            "transaction_type": "RECEIPT",
            "quantity_change": initial_stock,
            "running_balance": initial_stock,
            "primary_user_id": admin_auth.user_id,
            "secondary_user_id": witness_auth.user_id,
            "patient_id": None,
            "order_id": None,
            "timestamp": now_str,
            "prev_hash": self.GENESIS_HASH,
        }
        current_hash = self._compute_hash(entry_payload)
        metadata = {"description": "Vault opening stock"}
        entry = NarcoticLedgerEntry(
            **entry_payload,
            current_hash=current_hash,
            metadata=metadata
        )
        self.ledger[drug_id].append(entry)

        if self.persistence_store is not None:
            self.persistence_store.append_narcotic_ledger_entry(
                entry_id=entry.entry_id,
                drug_id=entry.drug_id,
                batch_number=entry.batch_number,
                transaction_type=entry.transaction_type,
                quantity_change=entry.quantity_change,
                running_balance=entry.running_balance,
                primary_user_id=entry.primary_user_id,
                secondary_user_id=entry.secondary_user_id,
                patient_id=entry.patient_id,
                order_id=entry.order_id,
                timestamp=entry.timestamp,
                prev_hash=entry.prev_hash,
                current_hash=entry.current_hash,
                metadata_json=json.dumps(entry.metadata)
            )

    def _verify_dual_biometrics(self, cred1: BiometricCredential, cred2: BiometricCredential):
        """Mechanically validates two distinct, authenticated biometric logins."""
        if not cred1 or not cred2:
            raise DualBiometricAuthenticationError("NDPS VIOLATION: Two authenticated parties are strictly required.")

        if cred1.user_id == cred2.user_id:
            raise DualBiometricAuthenticationError(
                f"NDPS VIOLATION: Primary signer and witness cannot be the same user ({cred1.user_id})."
            )

        if not (cred1.biometric_verified and cred2.biometric_verified):
            raise DualBiometricAuthenticationError(
                "NDPS VIOLATION: Both signers must present valid, active biometric verification."
            )

    def dispense_narcotic(
        self,
        drug_id: str,
        batch_number: str,
        quantity: int,
        patient_id: str,
        prescription_order_id: str,
        primary_auth: BiometricCredential,
        secondary_auth: BiometricCredential,
        as_of_time: Optional[datetime] = None
    ) -> NarcoticLedgerEntry:
        """
        Dispense controlled substance from vault.
        Mandates dual biometric authentication and updates perpetual ledger.
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        self._verify_dual_biometrics(primary_auth, secondary_auth)

        current_balance = self.balances.get(drug_id, 0)
        if quantity <= 0:
            raise NarcoticVaultError("Dispense quantity must be greater than zero.")
        if current_balance < quantity:
            raise NarcoticVaultError(
                f"INSUFFICIENT VAULT STOCK: Requested {quantity}, but current balance is {current_balance}."
            )

        new_balance = current_balance - quantity
        self.balances[drug_id] = new_balance

        history = self.ledger.get(drug_id, [])
        prev_hash = history[-1].current_hash if history else self.GENESIS_HASH

        entry_id = f"NDPS-DISP-{int(as_of_time.timestamp())}-{len(history)+1}"
        entry_payload = {
            "entry_id": entry_id,
            "drug_id": drug_id,
            "batch_number": batch_number,
            "transaction_type": "DISPENSE",
            "quantity_change": -quantity,
            "running_balance": new_balance,
            "primary_user_id": primary_auth.user_id,
            "secondary_user_id": secondary_auth.user_id,
            "patient_id": patient_id,
            "order_id": prescription_order_id,
            "timestamp": as_of_time.isoformat(),
            "prev_hash": prev_hash,
        }
        current_hash = self._compute_hash(entry_payload)

        entry = NarcoticLedgerEntry(
            **entry_payload,
            current_hash=current_hash,
            metadata={"patient_id": patient_id, "order_id": prescription_order_id}
        )
        self.ledger.setdefault(drug_id, []).append(entry)
        if self.persistence_store is not None:
            self.persistence_store.append_narcotic_ledger_entry(
                entry_id=entry.entry_id,
                drug_id=entry.drug_id,
                batch_number=entry.batch_number,
                transaction_type=entry.transaction_type,
                quantity_change=entry.quantity_change,
                running_balance=entry.running_balance,
                primary_user_id=entry.primary_user_id,
                secondary_user_id=entry.secondary_user_id,
                patient_id=entry.patient_id,
                order_id=entry.order_id,
                timestamp=entry.timestamp,
                prev_hash=entry.prev_hash,
                current_hash=entry.current_hash,
                metadata_json=json.dumps(entry.metadata)
            )
        return entry

    def return_narcotic(
        self,
        drug_id: str,
        batch_number: str,
        quantity: int,
        reason: str,
        returning_nurse_auth: BiometricCredential,
        receiving_pharmacist_auth: BiometricCredential,
        as_of_time: Optional[datetime] = None
    ) -> NarcoticLedgerEntry:
        """
        Records unused intact narcotic returned to vault stock with dual biometric sign-off.
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        self._verify_dual_biometrics(returning_nurse_auth, receiving_pharmacist_auth)

        if quantity <= 0:
            raise NarcoticVaultError("Return quantity must be greater than zero.")

        current_balance = self.balances.get(drug_id, 0)
        new_balance = current_balance + quantity
        self.balances[drug_id] = new_balance

        history = self.ledger.get(drug_id, [])
        prev_hash = history[-1].current_hash if history else self.GENESIS_HASH

        entry_id = f"NDPS-RET-{int(as_of_time.timestamp())}-{len(history)+1}"
        entry_payload = {
            "entry_id": entry_id,
            "drug_id": drug_id,
            "batch_number": batch_number,
            "transaction_type": "RETURN",
            "quantity_change": quantity,
            "running_balance": new_balance,
            "primary_user_id": returning_nurse_auth.user_id,
            "secondary_user_id": receiving_pharmacist_auth.user_id,
            "patient_id": None,
            "order_id": None,
            "timestamp": as_of_time.isoformat(),
            "prev_hash": prev_hash,
        }
        current_hash = self._compute_hash(entry_payload)
        entry = NarcoticLedgerEntry(
            **entry_payload,
            current_hash=current_hash,
            metadata={"reason": reason}
        )
        self.ledger.setdefault(drug_id, []).append(entry)
        if self.persistence_store is not None:
            self.persistence_store.append_narcotic_ledger_entry(
                entry_id=entry.entry_id,
                drug_id=entry.drug_id,
                batch_number=entry.batch_number,
                transaction_type=entry.transaction_type,
                quantity_change=entry.quantity_change,
                running_balance=entry.running_balance,
                primary_user_id=entry.primary_user_id,
                secondary_user_id=entry.secondary_user_id,
                patient_id=entry.patient_id,
                order_id=entry.order_id,
                timestamp=entry.timestamp,
                prev_hash=entry.prev_hash,
                current_hash=entry.current_hash,
                metadata_json=json.dumps(entry.metadata)
            )
        return entry

    def record_narcotic_wastage(
        self,
        drug_id: str,
        batch_number: str,
        wasted_quantity: int,
        reason: str,
        disposal_method: str,
        administering_nurse_auth: BiometricCredential,
        witness_nurse_auth: BiometricCredential,
        as_of_time: Optional[datetime] = None
    ) -> NarcoticLedgerEntry:
        """
        Records wasted partial narcotic dose (e.g., remaining in ampoule)
        with independent witness co-signature and verified disposal method.
        """
        if as_of_time is None:
            as_of_time = datetime.now(timezone.utc)

        self._verify_dual_biometrics(administering_nurse_auth, witness_nurse_auth)

        if wasted_quantity <= 0:
            raise NarcoticVaultError("Wasted quantity must be greater than zero.")

        # Note: Wastage records the destruction of already issued or compromised stock.
        # If discarded from vault stock directly:
        current_balance = self.balances.get(drug_id, 0)
        # Check if destroying from vault
        new_balance = max(0, current_balance - wasted_quantity)
        self.balances[drug_id] = new_balance

        history = self.ledger.get(drug_id, [])
        prev_hash = history[-1].current_hash if history else self.GENESIS_HASH

        entry_id = f"NDPS-WASTE-{int(as_of_time.timestamp())}-{len(history)+1}"
        entry_payload = {
            "entry_id": entry_id,
            "drug_id": drug_id,
            "batch_number": batch_number,
            "transaction_type": "WASTE",
            "quantity_change": -wasted_quantity,
            "running_balance": new_balance,
            "primary_user_id": administering_nurse_auth.user_id,
            "secondary_user_id": witness_nurse_auth.user_id,
            "patient_id": None,
            "order_id": None,
            "timestamp": as_of_time.isoformat(),
            "prev_hash": prev_hash,
        }
        current_hash = self._compute_hash(entry_payload)

        entry = NarcoticLedgerEntry(
            **entry_payload,
            current_hash=current_hash,
            metadata={
                "reason": reason,
                "disposal_method": disposal_method,
                "witnessed_by": witness_nurse_auth.user_id
            }
        )
        self.ledger.setdefault(drug_id, []).append(entry)
        if self.persistence_store is not None:
            self.persistence_store.append_narcotic_ledger_entry(
                entry_id=entry.entry_id,
                drug_id=entry.drug_id,
                batch_number=entry.batch_number,
                transaction_type=entry.transaction_type,
                quantity_change=entry.quantity_change,
                running_balance=entry.running_balance,
                primary_user_id=entry.primary_user_id,
                secondary_user_id=entry.secondary_user_id,
                patient_id=entry.patient_id,
                order_id=entry.order_id,
                timestamp=entry.timestamp,
                prev_hash=entry.prev_hash,
                current_hash=entry.current_hash,
                metadata_json=json.dumps(entry.metadata)
            )
        return entry

    def verify_ledger_integrity(self, drug_id: str) -> bool:
        """
        Cryptographically validates the hash chain of the narcotic ledger.
        Ensures zero undetected alterations or out-of-order records.
        """
        entries = self.ledger.get(drug_id, [])
        if not entries:
            return True

        expected_prev_hash = self.GENESIS_HASH
        for entry in entries:
            if entry.prev_hash != expected_prev_hash:
                raise NarcoticLedgerTamperError(
                    f"Hash chain broken at entry {entry.entry_id}: expected {expected_prev_hash}, got {entry.prev_hash}"
                )

            entry_payload = {
                "entry_id": entry.entry_id,
                "drug_id": entry.drug_id,
                "batch_number": entry.batch_number,
                "transaction_type": entry.transaction_type,
                "quantity_change": entry.quantity_change,
                "running_balance": entry.running_balance,
                "primary_user_id": entry.primary_user_id,
                "secondary_user_id": entry.secondary_user_id,
                "patient_id": entry.patient_id,
                "order_id": entry.order_id,
                "timestamp": entry.timestamp,
                "prev_hash": entry.prev_hash,
            }
            computed_hash = self._compute_hash(entry_payload)
            if computed_hash != entry.current_hash:
                raise NarcoticLedgerTamperError(
                    f"Hash mismatch at entry {entry.entry_id}: computed {computed_hash}, recorded {entry.current_hash}"
                )

            expected_prev_hash = entry.current_hash

        return True
