from datetime import datetime
import os.path
import plistlib
from django.test import TestCase
from django.utils.crypto import get_random_string
from zentral.contrib.inventory.models import MetaBusinessUnit, MetaMachine
from zentral.contrib.mdm.commands import ProfileList
from zentral.contrib.mdm.inventory import commit_update_tree, tree_from_payload
from zentral.contrib.mdm.models import Blueprint
from .utils import force_dep_enrollment_session


class ProfileListCommandTestCase(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.mbu = MetaBusinessUnit.objects.create(name=get_random_string(12))
        cls.mbu.create_enrollment_business_unit()
        cls.dep_enrollment_session, _, _ = force_dep_enrollment_session(
            cls.mbu, authenticated=True, completed=True, realm_user=True
        )
        cls.enrolled_device = cls.dep_enrollment_session.enrolled_device
        cls.blueprint = Blueprint.objects.create(
            name=get_random_string(32),
            collect_profiles=Blueprint.InventoryItemCollectionOption.ALL,
        )
        cls.enrolled_device.blueprint = cls.blueprint
        cls.enrolled_device.save()
        cls.device_information = plistlib.load(
            open(
                os.path.join(
                    os.path.dirname(__file__), "testdata/device_information.plist"
                ),
                "rb",
            )
        )
        cls.device_information["UDID"] = cls.enrolled_device.udid
        cls.device_information["SerialNumber"] = cls.enrolled_device.serial_number
        cls.profile_list = plistlib.load(
            open(
                os.path.join(os.path.dirname(__file__), "testdata/profile_list.plist"),
                "rb",
            )
        )

    def test_load_kwargs_store_result_false(self):
        cmd = ProfileList.create_for_device(
            self.enrolled_device,
            kwargs={"managed_only": True, "update_inventory": True},
        )
        self.assertTrue(cmd.managed_only)
        self.assertTrue(cmd.update_inventory)
        self.assertFalse(cmd.store_result)

    def test_load_kwargs_store_result_true(self):
        cmd = ProfileList.create_for_device(
            self.enrolled_device,
        )
        self.assertFalse(cmd.managed_only)
        self.assertFalse(cmd.update_inventory)
        self.assertTrue(cmd.store_result)

    def test_build_command(self):
        cmd = ProfileList.create_for_device(self.enrolled_device)
        response = cmd.build_http_response(self.dep_enrollment_session)
        payload = plistlib.loads(response.content)["Command"]
        self.assertEqual(payload["RequestType"], "ProfileList")
        self.assertFalse(payload["ManagedOnly"])

    def test_process_acknowledged_response_missing_cms(self):
        cmd = ProfileList.create_for_device(
            self.dep_enrollment_session.enrolled_device,
            kwargs={"update_inventory": True},
        )
        cmd.process_response(self.profile_list, self.dep_enrollment_session, self.mbu)
        cmd.db_command.refresh_from_db()
        self.assertIsNone(cmd.db_command.result)
        self.enrolled_device.refresh_from_db()
        self.assertIsNone(self.enrolled_device.profiles_updated_at)
        m = MetaMachine(self.enrolled_device.serial_number)
        self.assertEqual(len(m.snapshots), 0)

    def test_process_acknowledged_response_do_not_collect_profiles(self):
        start = datetime.utcnow()
        ms_tree = tree_from_payload(
            self.enrolled_device.udid,
            self.enrolled_device.serial_number,
            self.mbu,
            self.device_information["QueryResponses"],
        )
        commit_update_tree(self.enrolled_device, ms_tree, missing_ok=True)
        m0 = MetaMachine(self.enrolled_device.serial_number)
        ms0 = m0.snapshots[0]
        self.assertEqual(ms0.profiles.count(), 0)
        cmd = ProfileList.create_for_device(
            self.dep_enrollment_session.enrolled_device,
            kwargs={"update_inventory": True},
        )
        self.blueprint.collect_profiles = Blueprint.InventoryItemCollectionOption.NO
        self.blueprint.save()
        cmd.process_response(self.profile_list, self.dep_enrollment_session, self.mbu)
        cmd.db_command.refresh_from_db()
        self.assertIsNone(cmd.db_command.result)
        self.enrolled_device.refresh_from_db()
        self.assertTrue(self.enrolled_device.profiles_updated_at > start)
        m = MetaMachine(self.enrolled_device.serial_number)
        ms = m.snapshots[0]
        self.assertEqual(ms.profiles.count(), 0)

    def test_process_acknowledged_response_collect_profiles(self):
        start = datetime.utcnow()
        ms_tree = tree_from_payload(
            self.enrolled_device.udid,
            self.enrolled_device.serial_number,
            self.mbu,
            self.device_information["QueryResponses"],
        )
        commit_update_tree(self.enrolled_device, ms_tree, missing_ok=True)
        m0 = MetaMachine(self.enrolled_device.serial_number)
        ms0 = m0.snapshots[0]
        self.assertEqual(ms0.profiles.count(), 0)
        cmd = ProfileList.create_for_device(
            self.dep_enrollment_session.enrolled_device,
            kwargs={"update_inventory": True},
        )
        self.assertEqual(
            self.enrolled_device.blueprint.collect_profiles,
            Blueprint.InventoryItemCollectionOption.ALL,
        )
        cmd.process_response(self.profile_list, self.dep_enrollment_session, self.mbu)
        cmd.db_command.refresh_from_db()
        self.assertIsNone(cmd.db_command.result)
        self.enrolled_device.refresh_from_db()
        self.assertTrue(self.enrolled_device.profiles_updated_at > start)
        m = MetaMachine(self.enrolled_device.serial_number)
        ms = m.snapshots[0]
        i = 0
        for profile in ms.profiles.select_related("signed_by__signed_by").all():
            i += 1
            self.assertEqual(profile.signed_by.common_name, "zentral")
            self.assertEqual(profile.signed_by.signed_by.common_name, "Zentral CA")
            if profile.uuid == "db2004f8-9e9f-4043-8a6f-339cfd7d7891":
                self.assertEqual(
                    profile.serialize(),
                    {
                        "description": "Google Santa configuration for Zentral",
                        "display_name": "Zentral - Santa configuration",
                        "encrypted": False,
                        "has_removal_passcode": False,
                        "identifier": "com.example.zentral.santa_configuration",
                        "organization": "Zentral",
                        "payloads": [
                            {
                                "identifier": "com.example.zentral.santa_configuration",
                                "type": "com.apple.ManagedClient.preferences",
                                "uuid": "9e21e537-5848-4ef5-914f-a626540836b6",
                            }
                        ],
                        "removal_disallowed": True,
                        "signed_by": {
                            "common_name": "zentral",
                            "sha_1": "f373928e75dfa460726c92c3263e664816b504d5",
                            "signed_by": {
                                "common_name": "Zentral CA",
                                "organization": "Zentral",
                                "organizational_unit": "IT",
                                "sha_1": "9a2dc1b26c23776aa828aaaae6d5284981e81f8a",
                                "valid_from": "2017-10-16T15:14:38",
                                "valid_until": "2027-10-14T15:14:38",
                            },
                            "valid_from": "2019-06-27T10:56:05",
                            "valid_until": "2029-06-24T10:56:05",
                        },
                        "uuid": "db2004f8-9e9f-4043-8a6f-339cfd7d7891",
                    },
                )
            elif profile.uuid == "075aac62-b261-46a7-9f0c-f9a69f13f7a7":
                self.assertEqual(
                    profile.serialize(),
                    {
                        "display_name": "Zentral - MDM enrollment",
                        "encrypted": False,
                        "has_removal_passcode": False,
                        "identifier": "com.example.zentral.mdm",
                        "payloads": [
                            {
                                "identifier": "com.example.zentral.mdm",
                                "type": "com.apple.mdm",
                                "uuid": "e93d0c41-632c-49e9-abe2-0a8a2b72e16e",
                            },
                            {
                                "identifier": "com.example.zentral.scep",
                                "type": "com.apple.security.scep",
                                "uuid": "04effe71-4c36-4bdd-b235-a3fa811abf5f",
                            },
                            {
                                "identifier": "com.example.zentral.tls-root-ca-cert",
                                "type": "com.apple.security.pem",
                                "uuid": "7b0f4651-ec41-48ae-be5f-a209cb9fd600",
                            },
                        ],
                        "removal_disallowed": False,
                        "signed_by": {
                            "common_name": "zentral",
                            "sha_1": "f373928e75dfa460726c92c3263e664816b504d5",
                            "signed_by": {
                                "common_name": "Zentral CA",
                                "organization": "Zentral",
                                "organizational_unit": "IT",
                                "sha_1": "9a2dc1b26c23776aa828aaaae6d5284981e81f8a",
                                "valid_from": "2017-10-16T15:14:38",
                                "valid_until": "2027-10-14T15:14:38",
                            },
                            "valid_from": "2019-06-27T10:56:05",
                            "valid_until": "2029-06-24T10:56:05",
                        },
                        "uuid": "075aac62-b261-46a7-9f0c-f9a69f13f7a7",
                    },
                )
            else:
                raise ValueError
        self.assertEqual(i, 2)
