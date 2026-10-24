from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ReceiverPostReceiver")


@_attrs_define
class ReceiverPostReceiver:
    """Crear una nueva cuenta de cobro asociada a un integrador. Necesita datos de la cuenta de usuario asociada, datos de
    facturación y datos de contacto.

        Attributes:
            admin_first_name (str): Nombre de pila del administrador de la cuenta de cobro a crear. Example: Nombre.
            admin_last_name (str): Apellido del administrador de la cuenta de cobro a crear. Example: Apellido.
            admin_email (str): Correo electrónico del administrador de la cuenta de cobro a crear. Example: admin@email.com.
            country_code (str): Código alfanumérico de dos caracteres ISO 3166-1 del país de la cuenta de cobro a crear.
                Example: CL.
            business_identifier (str): Identificador tributario del cobrador asociado a la cuenta de cobro a crear. Example:
                99.999.999-9.
            business_category (str): Categoría tributaria o rubro tributario del cobrador asociado a la cuenta de cobro a
                crear. Example: VENTA AL POR MAYOR DE FRUTAS Y VERDURAS.
            business_name (str): Nombre tributario del cobrador asociado a la cuenta de cobro a crear. Example: Nombre
                Tributario.
            business_phone (str): Teléfono del cobrador asociado a la cuenta de cobro a crear. Example: +56988887777.
            business_address_line_1 (str): Dirección del cobrador de la cuenta de cobro a crear. Example: Calle principal
                1111.
            business_address_line_2 (str): Segunda línea de la dirección del cobrador de la cuenta de cobro a crear.
                Example: Oficina 3-A.
            business_address_line_3 (str): Tercera línea de la dirección del cobrador de la cuenta de cobro a crear.
                Example: Santiago.
            contact_full_name (str): Nombre del contacto del cobrador. Example: Nombre Contacto.
            contact_job_title (str): Cargo del contacto del cobrador. Example: Tesorero.
            contact_email (str): Correo electrónico del contacto del cobrador. Example: contacto@email.com.
            contact_phone (str): Teléfono del contacto del cobrador. Example: +56955553333.
            bank_account_bank_id (str | Unset): Identificador del banco. Example: SDdGj.
            bank_account_type (str | Unset): Tipo de cuenta. Es obligatorio si se utiliza el modelo alternativo de
                integrador de confianza. Example: Cuenta Corriente.
            bank_account_identifier (str | Unset): Identificador personal del dueño de la cuenta de banco. Example:
                11.333.555-7.
            bank_account_name (str | Unset): Nombre de la cuenta de banco. Example: Alias Cuenta.
            bank_account_number (str | Unset): Número de la cuenta en el banco. Example: 00347909823.
            notify_url (str | Unset): URL por omisión para el webservice donde se notificará el pago. Example:
                http://micomercio.com/account/notify_url.
            rendition_url (str | Unset): URL para el webservice donde se notificará la rendición. Example:
                http://micomercio.com/account/rendition_url.
    """

    admin_first_name: str
    admin_last_name: str
    admin_email: str
    country_code: str
    business_identifier: str
    business_category: str
    business_name: str
    business_phone: str
    business_address_line_1: str
    business_address_line_2: str
    business_address_line_3: str
    contact_full_name: str
    contact_job_title: str
    contact_email: str
    contact_phone: str
    bank_account_bank_id: str | Unset = UNSET
    bank_account_type: str | Unset = UNSET
    bank_account_identifier: str | Unset = UNSET
    bank_account_name: str | Unset = UNSET
    bank_account_number: str | Unset = UNSET
    notify_url: str | Unset = UNSET
    rendition_url: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        admin_first_name = self.admin_first_name

        admin_last_name = self.admin_last_name

        admin_email = self.admin_email

        country_code = self.country_code

        business_identifier = self.business_identifier

        business_category = self.business_category

        business_name = self.business_name

        business_phone = self.business_phone

        business_address_line_1 = self.business_address_line_1

        business_address_line_2 = self.business_address_line_2

        business_address_line_3 = self.business_address_line_3

        contact_full_name = self.contact_full_name

        contact_job_title = self.contact_job_title

        contact_email = self.contact_email

        contact_phone = self.contact_phone

        bank_account_bank_id = self.bank_account_bank_id

        bank_account_type = self.bank_account_type

        bank_account_identifier = self.bank_account_identifier

        bank_account_name = self.bank_account_name

        bank_account_number = self.bank_account_number

        notify_url = self.notify_url

        rendition_url = self.rendition_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "admin_first_name": admin_first_name,
                "admin_last_name": admin_last_name,
                "admin_email": admin_email,
                "country_code": country_code,
                "business_identifier": business_identifier,
                "business_category": business_category,
                "business_name": business_name,
                "business_phone": business_phone,
                "business_address_line_1": business_address_line_1,
                "business_address_line_2": business_address_line_2,
                "business_address_line_3": business_address_line_3,
                "contact_full_name": contact_full_name,
                "contact_job_title": contact_job_title,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
            }
        )
        if bank_account_bank_id is not UNSET:
            field_dict["bank_account_bank_id"] = bank_account_bank_id
        if bank_account_type is not UNSET:
            field_dict["bank_account_type"] = bank_account_type
        if bank_account_identifier is not UNSET:
            field_dict["bank_account_identifier"] = bank_account_identifier
        if bank_account_name is not UNSET:
            field_dict["bank_account_name"] = bank_account_name
        if bank_account_number is not UNSET:
            field_dict["bank_account_number"] = bank_account_number
        if notify_url is not UNSET:
            field_dict["notify_url"] = notify_url
        if rendition_url is not UNSET:
            field_dict["rendition_url"] = rendition_url

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        admin_first_name = d.pop("admin_first_name")

        admin_last_name = d.pop("admin_last_name")

        admin_email = d.pop("admin_email")

        country_code = d.pop("country_code")

        business_identifier = d.pop("business_identifier")

        business_category = d.pop("business_category")

        business_name = d.pop("business_name")

        business_phone = d.pop("business_phone")

        business_address_line_1 = d.pop("business_address_line_1")

        business_address_line_2 = d.pop("business_address_line_2")

        business_address_line_3 = d.pop("business_address_line_3")

        contact_full_name = d.pop("contact_full_name")

        contact_job_title = d.pop("contact_job_title")

        contact_email = d.pop("contact_email")

        contact_phone = d.pop("contact_phone")

        bank_account_bank_id = d.pop("bank_account_bank_id", UNSET)

        bank_account_type = d.pop("bank_account_type", UNSET)

        bank_account_identifier = d.pop("bank_account_identifier", UNSET)

        bank_account_name = d.pop("bank_account_name", UNSET)

        bank_account_number = d.pop("bank_account_number", UNSET)

        notify_url = d.pop("notify_url", UNSET)

        rendition_url = d.pop("rendition_url", UNSET)

        receiver_post_receiver = cls(
            admin_first_name=admin_first_name,
            admin_last_name=admin_last_name,
            admin_email=admin_email,
            country_code=country_code,
            business_identifier=business_identifier,
            business_category=business_category,
            business_name=business_name,
            business_phone=business_phone,
            business_address_line_1=business_address_line_1,
            business_address_line_2=business_address_line_2,
            business_address_line_3=business_address_line_3,
            contact_full_name=contact_full_name,
            contact_job_title=contact_job_title,
            contact_email=contact_email,
            contact_phone=contact_phone,
            bank_account_bank_id=bank_account_bank_id,
            bank_account_type=bank_account_type,
            bank_account_identifier=bank_account_identifier,
            bank_account_name=bank_account_name,
            bank_account_number=bank_account_number,
            notify_url=notify_url,
            rendition_url=rendition_url,
        )

        receiver_post_receiver.additional_properties = d
        return receiver_post_receiver

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
