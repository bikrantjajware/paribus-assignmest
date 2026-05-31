import requests
from flask import current_app

from app.db import DBHospital
from app.schemas import HospitalRow

class HospitalAPIClient:
    def __init__(self):
        self.base_url: str | None = None
        self.session: requests.Session | None = None

    def init_app(self, app):
        """Configure the client once the Flask app and its config are ready."""
        self.base_url = app.config["HOSPITAL_API_BASE_URL"].rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs):
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            timeout=10,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()


    def create_hospital(self, hospital: HospitalRow, batch_id: str):
        return self._request("POST", "/hospitals/", json={
            "name": hospital.name,
            "address": hospital.address,
            "phone": hospital.phone,
            "creation_batch_id": batch_id,
        })
    
    def activate_hospitals_in_batch(self, batch_id: str):
        return self._request("PATCH", f"/hospitals/batch/{batch_id}/activate")

    def get_hospital(self, hospital_id: int):
        return self._request("GET", f"/hospitals/{hospital_id}")

    def update_hospital(self, hospital_id: int, data: dict):
        return self._request("PUT", f"/hospitals/{hospital_id}", json=data)

    def delete_hospital(self, hospital_id: int):
        return self._request("DELETE", f"/hospitals/{hospital_id}")
