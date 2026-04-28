from app.services.credential_service import CredentialService


def test_credential_service_round_trips_plaintext_for_runtime_use():
    service = CredentialService(secret_key="unit-test-key")

    blob = service.encrypt_secret("netops-password")
    restored = service.decrypt_secret(blob)

    assert blob != "netops-password"
    assert restored == "netops-password"
