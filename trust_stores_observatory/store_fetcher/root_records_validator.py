import logging
from typing import Tuple, List, Set, Union, Type

from cryptography.hazmat.primitives import hashes

from trust_stores_observatory.certificates_repository import RootCertificatesRepository, CertificateNotFoundError
from trust_stores_observatory.trust_store import RootCertificateRecord


class RootRecordsValidator:
    """Given a list of subject names and SHA 256 fingerprints scraped from a web page, try to look for each
    certificate in the local certificates repository and if the certificate was found, normalize the subject name
    we use to refer to this certificate.
    """

    @staticmethod
    def validate_with_repository(
            certs_repo: RootCertificatesRepository,
            hash_algorithm: Union[Type[hashes.SHA1], Type[hashes.SHA256]],
            parsed_root_records: List[Tuple[str, bytes]],
    ) -> Set[RootCertificateRecord]:
        validated_root_records = set()

        for scraped_subj_name, fingerprint in parsed_root_records:
            try:
                cert = certs_repo.lookup_certificate_with_fingerprint(fingerprint, hash_algorithm)
                validated_root_records.add(RootCertificateRecord.from_certificate(cert))
            except CertificateNotFoundError:
                # We have never seen this certificate - use whatever name we scraped from the page
                logging.error(f'Could not find certificate "{scraped_subj_name}" in local repository')
                record = RootCertificateRecord.from_scraped_record(scraped_subj_name, fingerprint)
                validated_root_records.add(record)
            except ValueError as e:
                if 'Unsupported ASN1 string type' in e.args[0]:
                    # Could not parse the certificate: https://github.com/pyca/cryptography/issues/3542
                    logging.error(f'Parsing error for certificate "{scraped_subj_name}"')
                    # Give up and just use the scraped name
                    record = RootCertificateRecord.from_scraped_record(scraped_subj_name, fingerprint)
                    validated_root_records.add(record)
                else:
                    raise

        return validated_root_records