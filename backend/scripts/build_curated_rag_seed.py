from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEED_DIR = ROOT / "app" / "data" / "rag_seed"


def chunk(
    chunk_id: str,
    title: str,
    section: str,
    content: str,
    keywords: list[str],
    language: str = "ko",
) -> dict:
    return {
        "chunk_id": chunk_id,
        "section": section,
        "content": content,
        "keywords": keywords,
        "language": language,
        "metadata": {
            "title": title,
            "chunking_strategy": "curated_section_chunking",
            "source_use": "rag_consultation_preparation",
        },
    }


def doc(
    doc_id: str,
    title: str,
    source_org: str,
    document_type: str,
    language: str,
    version: str,
    chunks: list[dict],
    source_url: str | None = None,
) -> dict:
    return {
        "document_id": doc_id,
        "title": title,
        "source_org": source_org,
        "document_type": document_type,
        "language": language,
        "version": version,
        "source_url": source_url,
        "metadata": {
            "curation_note": "BADA 임금체불 상담 전 준비 챗봇에 필요한 범위로 요약 청킹한 seed 데이터",
        },
        "chunks": chunks,
    }


def subrogation_form_seed() -> dict:
    title = "대지급금 등 확인신청서"
    return {
        "documents": [
            doc(
                "molab-subrogation-confirmation-application-form",
                title,
                "고용노동부",
                "official_form",
                "ko",
                "임금채권보장법 시행규칙 별지 제4호서식",
                [
                    chunk(
                        "subrogation-form-overview",
                        title,
                        "서식 개요",
                        "대지급금 등 확인신청서는 임금채권보장제도 관련 확인을 신청할 때 사용하는 공식 서식이다. BADA에서는 사용자가 상담 전 어떤 항목을 준비해야 하는지 안내하는 참고자료로 활용한다.",
                        ["대지급금", "확인신청서", "임금채권보장법", "서식"],
                    ),
                    chunk(
                        "subrogation-form-applicant",
                        title,
                        "신청인 정보",
                        "신청인 항목에는 성명, 주민등록번호 또는 외국인등록번호, 주소, 연락처 등 본인을 식별할 수 있는 정보를 적는다. 외국인근로자는 체류자격과 연락 가능한 전화번호를 함께 정리해 두면 상담이 수월하다.",
                        ["신청인", "외국인등록번호", "체류자격", "연락처"],
                    ),
                    chunk(
                        "subrogation-form-employer",
                        title,
                        "대상 사업주 정보",
                        "대상 사업주 항목에는 사업장명, 대표자, 사업장 주소, 연락처 등 사업장을 확인할 수 있는 정보를 적는다. 사업장 정보가 불명확하면 근로계약서, 급여명세서, 사업장 사진 등 보조자료가 도움이 될 수 있다.",
                        ["사업주", "사업장명", "대표자", "사업장 주소"],
                    ),
                    chunk(
                        "subrogation-form-claim",
                        title,
                        "확인 신청 사항",
                        "확인 신청 사항에는 체불 임금, 퇴직금, 휴업수당 등 확인받으려는 금액과 기간을 사실관계 중심으로 정리한다. 금액은 확정 판단처럼 단정하지 말고 자료 기준의 차이와 산정 근거를 함께 표시하는 것이 좋다.",
                        ["체불 임금", "퇴직금", "휴업수당", "금액", "기간"],
                    ),
                    chunk(
                        "subrogation-form-attachments",
                        title,
                        "첨부자료",
                        "신청 전에는 근로계약서, 임금명세서, 통장 입금내역, 출퇴근 기록, 사업주와의 대화자료 등 사실관계를 보여주는 자료를 함께 정리하는 것이 좋다. BADA의 Evidence Pack은 이 첨부자료 목록을 상담 전 점검하는 데 활용할 수 있다.",
                        ["첨부자료", "근로계약서", "임금명세서", "입금내역", "출퇴근 기록"],
                    ),
                    chunk(
                        "subrogation-form-consent",
                        title,
                        "자료 제공 동의",
                        "서식에는 행정기관이 필요한 자료를 확인하거나 제공받는 것에 관한 동의 항목이 포함될 수 있다. 사용자는 어떤 개인정보가 사용되는지 확인하고, 모르는 항목은 상담기관에 질문하도록 안내하는 것이 적절하다.",
                        ["자료 제공", "개인정보", "동의", "행정기관"],
                    ),
                    chunk(
                        "subrogation-form-warning",
                        title,
                        "작성 시 주의사항",
                        "대지급금 관련 서식은 사실과 다른 내용으로 신청하면 문제가 될 수 있으므로, BADA는 법적 판단이나 수급 가능 여부를 단정하지 않고 자료 정리와 질문 목록 준비만 지원한다.",
                        ["주의사항", "사실관계", "부정수급", "법적 판단 금지"],
                    ),
                ],
            )
        ]
    }


def labor_guides_seed() -> list[dict]:
    return [
        doc(
            "molab-wage-statement-prep",
            "임금명세서와 입금내역 상담 준비",
            "고용노동부",
            "official_guide_summary",
            "ko",
            "mvp-2026-06",
            [
                chunk(
                    "wage-statement-compare",
                    "임금명세서와 입금내역 상담 준비",
                    "임금명세서 확인",
                    "상담 전에는 급여명세서, 실제 입금내역, 근로계약서의 임금 조건을 함께 정리하는 것이 좋다. 명세서 금액과 실제 입금액 사이에 차이가 있으면 차이 금액, 지급일, 공제 항목을 같은 기간 기준으로 표시한다.",
                    ["임금명세서", "입금내역", "급여", "차이", "공제", "상담 준비"],
                ),
                chunk(
                    "wage-deduction-check",
                    "임금명세서와 입금내역 상담 준비",
                    "공제 항목 확인",
                    "기숙사비, 식비, 작업복비처럼 임금에서 빠진 항목은 항목명, 금액, 설명받은 내용, 동의 자료가 있는지 정리한다. 공제의 적법성이나 체불 여부는 BADA가 단정하지 않고 상담기관에서 확인해야 한다.",
                    ["공제", "기숙사비", "식비", "작업복비", "동의", "상담기관"],
                ),
            ],
        ),
        doc(
            "molab-labor-office-consultation-prep",
            "고용노동부 상담 전 준비자료",
            "고용노동부",
            "official_guide_summary",
            "ko",
            "mvp-2026-06",
            [
                chunk(
                    "labor-office-speaking-order",
                    "고용노동부 상담 전 준비자료",
                    "상담 순서",
                    "상담할 때는 사업장명과 근무 기간을 먼저 말하고, 약속한 임금과 실제 입금액을 설명한 뒤, 급여명세서와 입금내역의 차이 및 공제 항목을 보여주는 순서가 좋다.",
                    ["상담", "순서", "사업장", "근무 기간", "임금", "입금액"],
                ),
                chunk(
                    "labor-office-missing-materials",
                    "고용노동부 상담 전 준비자료",
                    "누락 자료",
                    "자료가 부족해도 현재 가진 자료를 먼저 정리해 상담할 수 있다. 다만 근무시간 기록, 계약서 첫 페이지, 사업장 정보, 공제 설명 자료, 대화 캡처 원본이 있으면 상담 시 확인에 도움이 된다.",
                    ["누락 자료", "근무시간 기록", "계약서", "사업장 정보", "대화 캡처"],
                ),
            ],
        ),
        doc(
            "bada-safety-legal-judgment-policy",
            "BADA 법률 판단 제한 정책",
            "BADA",
            "product_policy",
            "ko",
            "mvp-2026-06",
            [
                chunk(
                    "bada-no-legal-judgment",
                    "BADA 법률 판단 제한 정책",
                    "표현 제한",
                    "BADA는 법률 판단을 제공하지 않는다. 위법 여부, 체불 확정, 받을 금액 확정, 소송 또는 즉시 신고 지시처럼 결론을 단정하는 표현은 피하고, 상담기관 또는 전문가 확인이 필요하다고 안내한다.",
                    ["법률 판단", "위법", "체불 확정", "단정 금지", "상담기관", "전문가"],
                )
            ],
        ),
    ]


def labor_forms_and_laws_seed() -> dict:
    docs: list[dict] = []

    petition_title = "진정서 양식"
    docs.append(
        doc(
            "molab-labor-petition-form",
            petition_title,
            "고용노동부",
            "official_form",
            "ko",
            "진정서 양식",
            [
                chunk(
                    "petition-form-purpose",
                    petition_title,
                    "서식 목적",
                    "진정서는 사용자가 근로 관련 사실관계를 행정기관에 알리고 확인을 요청할 때 쓰는 서식이다. 임금체불 상담에서는 누가, 어디에서, 언제부터 언제까지 일했고, 어떤 금액 차이가 있는지 순서대로 정리하는 것이 중요하다.",
                    ["진정서", "임금체불", "사실관계", "상담 준비"],
                ),
                chunk(
                    "petition-form-complainant",
                    petition_title,
                    "진정인 정보",
                    "진정인 정보에는 이름, 생년월일 또는 외국인등록번호, 주소, 연락처, 국적, 체류자격 등 본인을 확인할 수 있는 정보를 적는다. 외국인근로자는 통역 필요 여부와 선호 언어도 함께 메모해 두면 좋다.",
                    ["진정인", "외국인등록번호", "국적", "체류자격", "통역"],
                ),
                chunk(
                    "petition-form-employer",
                    petition_title,
                    "피진정인 정보",
                    "피진정인 정보에는 사업장명, 대표자, 사업장 주소, 연락처를 적는다. 사업장 정보가 부족하면 근로계약서 첫 페이지, 급여명세서, 사업장 사진, 채용 공고 등을 보조자료로 준비할 수 있다.",
                    ["피진정인", "사업장명", "대표자", "사업장 주소"],
                ),
                chunk(
                    "petition-form-facts",
                    petition_title,
                    "진정 내용 작성",
                    "진정 내용은 감정 표현보다 사실관계 중심으로 작성한다. 근무 기간, 업무, 약속한 임금, 실제 입금액, 급여명세서 금액, 공제 항목, 차이 금액을 시간 순서로 정리하면 상담자가 핵심을 빠르게 파악할 수 있다.",
                    ["진정 내용", "근무 기간", "약속 임금", "입금액", "공제 항목"],
                ),
                chunk(
                    "petition-form-evidence-list",
                    petition_title,
                    "증빙자료 목록",
                    "진정서와 함께 제출하거나 상담 시 보여줄 자료로는 근로계약서, 급여명세서, 계좌 입금내역, 출퇴근 기록, 업무 지시 메시지, 사업주와의 대화자료 등이 있다. BADA는 이 자료들을 Evidence Pack으로 묶어 상담 전 확인을 돕는다.",
                    ["증빙자료", "근로계약서", "급여명세서", "입금내역", "출퇴근 기록"],
                ),
            ],
        )
    )

    confirmation_title = "체불 임금등ㆍ사업주 확인서 발급신청서"
    docs.append(
        doc(
            "molab-unpaid-wage-employer-confirmation-application-form",
            confirmation_title,
            "고용노동부",
            "official_form",
            "ko",
            "임금채권보장법 시행규칙 서식 7의2",
            [
                chunk(
                    "employer-confirmation-purpose",
                    confirmation_title,
                    "서식 목적",
                    "체불 임금등ㆍ사업주 확인서 발급신청서는 체불 임금 등과 사업주 관련 사실을 확인받기 위해 사용하는 공식 서식이다. BADA에서는 사용자가 상담 전에 필요한 정보와 증빙자료를 정리하도록 안내하는 데 활용한다.",
                    ["체불 임금등", "사업주 확인서", "발급신청서", "상담 준비"],
                ),
                chunk(
                    "employer-confirmation-worker-info",
                    confirmation_title,
                    "근로자 정보",
                    "근로자 정보에는 성명, 생년월일 또는 외국인등록번호, 주소, 연락처 등 본인 확인 정보를 정리한다. 외국인근로자는 국적, 체류자격, 통역 필요 여부도 함께 준비하면 좋다.",
                    ["근로자 정보", "외국인등록번호", "국적", "체류자격"],
                ),
                chunk(
                    "employer-confirmation-workplace-info",
                    confirmation_title,
                    "사업장 정보",
                    "사업장 정보에는 사업장명, 대표자, 소재지, 연락처 등 사용자를 특정할 수 있는 내용을 적는다. 사업장 정보가 부족하면 근로계약서, 급여명세서, 사업장 사진, 채용 공고를 함께 확인한다.",
                    ["사업장 정보", "대표자", "소재지", "사용자"],
                ),
                chunk(
                    "employer-confirmation-wage-period",
                    confirmation_title,
                    "임금 기간과 금액",
                    "신청 전에는 체불이 의심되는 기간, 약속 임금, 급여명세서 금액, 실제 입금액, 공제 항목을 표로 정리한다. BADA는 금액 차이를 보여줄 수 있지만, 체불 여부의 최종 판단은 고용노동부 또는 전문가가 확인해야 한다.",
                    ["임금 기간", "급여명세서", "입금액", "공제 항목", "최종 판단"],
                ),
                chunk(
                    "employer-confirmation-attachments",
                    confirmation_title,
                    "첨부자료",
                    "첨부자료로는 근로계약서, 임금명세서, 계좌 입금내역, 출퇴근 기록, 문자 또는 메신저 대화, 사업장 정보가 보이는 자료가 도움이 된다. 자료가 부족한 경우에는 어떤 자료가 없는지도 상담 시 말할 수 있게 정리한다.",
                    ["첨부자료", "근로계약서", "임금명세서", "입금내역", "대화자료"],
                ),
            ],
        )
    )

    lsa_title = "근로기준법"
    docs.append(
        doc(
            "law-labor-standards-act-20520-20251023",
            lsa_title,
            "국가법령정보센터",
            "law",
            "ko",
            "법률 제20520호, 2025-10-23 시행",
            [
                chunk(
                    "lsa-purpose-and-standard",
                    lsa_title,
                    "목적과 근로조건 기준",
                    "근로기준법은 근로조건의 최저기준을 정해 근로자의 기본적 생활을 보장하고 향상시키는 것을 목적으로 한다. BADA는 이 법을 법률 판단 근거로 단정하지 않고 상담 전 확인할 쟁점을 정리하는 참고자료로 사용한다.",
                    ["근로기준법", "근로조건", "최저기준", "상담 전 확인"],
                ),
                chunk(
                    "lsa-worker-employer-wage",
                    lsa_title,
                    "근로자ㆍ사용자ㆍ임금",
                    "근로기준법상 근로자, 사용자, 임금의 개념은 상담에서 기본 전제가 된다. 임금 관련 상담에서는 누가 사용자이고, 어떤 금품이 근로의 대가로 지급되기로 했는지, 실제 지급 내역이 어떤지 정리해야 한다.",
                    ["근로자", "사용자", "임금", "근로의 대가"],
                ),
                chunk(
                    "lsa-written-terms",
                    lsa_title,
                    "근로조건 명시",
                    "근로계약을 체결할 때 임금, 소정근로시간, 휴일, 연차유급휴가 등 주요 근로조건은 명확히 제시되어야 한다. 상담 전에는 근로계약서와 실제 근무ㆍ지급 내역이 일치하는지 나란히 확인하는 것이 좋다.",
                    ["근로조건 명시", "근로계약서", "임금", "소정근로시간"],
                ),
                chunk(
                    "lsa-wage-payment",
                    lsa_title,
                    "임금 지급 원칙",
                    "임금 지급과 관련해서는 약속된 지급일, 실제 지급일, 지급 방식, 공제 내역을 확인해야 한다. BADA는 급여명세서와 입금내역의 차이를 정리할 수 있지만, 해당 차이의 법적 성격은 상담기관에서 확인해야 한다.",
                    ["임금 지급", "지급일", "입금내역", "공제", "법적 성격"],
                ),
                chunk(
                    "lsa-wage-ledger-statement",
                    lsa_title,
                    "임금대장과 임금명세서",
                    "임금 관련 분쟁 상담에서는 임금명세서, 임금대장, 계좌 입금내역이 핵심 자료가 될 수 있다. 금액, 항목, 공제 사유, 지급일을 같은 기간끼리 맞춰 정리하면 상담자가 차이를 확인하기 쉽다.",
                    ["임금대장", "임금명세서", "계좌 입금내역", "공제 사유"],
                ),
                chunk(
                    "lsa-equal-treatment-foreign-worker",
                    lsa_title,
                    "균등처우와 외국인근로자 상담",
                    "근로기준법의 기본 원칙은 국적이나 사회적 신분 등을 이유로 근로조건을 부당하게 차별하지 않는 방향의 기준을 둔다. 외국인근로자 상담에서는 국적, 언어, 체류자격과 별개로 근무 사실과 임금 자료를 중심으로 정리한다.",
                    ["균등처우", "외국인근로자", "국적", "근로조건"],
                ),
            ],
        )
    )

    foreign_law_title = "외국인근로자의 고용 등에 관한 법률"
    docs.append(
        doc(
            "law-foreign-worker-employment-act-21065-20251001",
            foreign_law_title,
            "국가법령정보센터",
            "law",
            "ko",
            "법률 제21065호, 2025-10-01 시행",
            [
                chunk(
                    "fwea-purpose",
                    foreign_law_title,
                    "법의 목적",
                    "외국인근로자의 고용 등에 관한 법률은 외국인근로자의 체계적인 도입과 관리, 권익 보호와 관련된 절차를 정한다. BADA에서는 외국인근로자의 상담 준비와 사업장 정보 정리에 필요한 배경 자료로 활용한다.",
                    ["외국인근로자", "고용", "권익 보호", "상담 준비"],
                ),
                chunk(
                    "fwea-employment-permit",
                    foreign_law_title,
                    "고용허가와 사업장 정보",
                    "외국인근로자 상담에서는 고용허가, 사업장명, 대표자, 근무 장소, 담당 업무, 근무 기간을 함께 정리해야 한다. 사업장 변경이나 고용 관련 이력이 있으면 그 순서도 별도로 메모한다.",
                    ["고용허가", "사업장명", "근무 장소", "사업장 변경"],
                ),
                chunk(
                    "fwea-employment-contract",
                    foreign_law_title,
                    "근로계약",
                    "외국인근로자의 근로계약은 임금, 근로시간, 업무 내용, 근무 장소 등 상담의 핵심 자료다. 계약서가 외국어로 되어 있거나 번역본이 있으면 원문과 번역본을 함께 준비하는 것이 좋다.",
                    ["근로계약", "임금", "근로시간", "번역본"],
                ),
                chunk(
                    "fwea-workplace-change",
                    foreign_law_title,
                    "사업장 변경 관련 쟁점",
                    "외국인근로자가 사업장 변경을 고민하는 경우에는 변경 사유, 현재 사업장과의 대화 내용, 임금 지급 내역, 근무 환경 관련 자료를 정리해야 한다. 가능 여부는 관계기관 상담을 통해 확인해야 한다.",
                    ["사업장 변경", "변경 사유", "관계기관 상담", "근무 환경"],
                ),
                chunk(
                    "fwea-education-insurance-support",
                    foreign_law_title,
                    "교육ㆍ보험ㆍ지원",
                    "외국인근로자 제도에는 취업교육, 보험, 상담 지원 등 권익 보호 장치가 포함될 수 있다. 사용자는 본인이 가입했거나 안내받은 보험, 교육자료, 상담기관 연락처를 함께 보관하는 것이 좋다.",
                    ["취업교육", "보험", "상담 지원", "권익 보호"],
                ),
            ],
        )
    )

    amendment_title = "상습체불 근절을 위한 근로기준법 주요 개정내용"
    docs.append(
        doc(
            "molab-labor-standards-amendment-habitual-wage-arrears-2025",
            amendment_title,
            "고용노동부",
            "official_guide",
            "ko",
            "근로개선지도1과 안내자료",
            [
                chunk(
                    "habitual-arrears-overview",
                    amendment_title,
                    "자료 개요",
                    "상습체불 근절 관련 안내자료는 임금체불 예방과 제재 강화의 방향을 설명한다. BADA에서는 사용자의 사건을 법적으로 판단하기보다 체불 의심 자료를 어떻게 정리해 상담할지 안내하는 근거 자료로 사용한다.",
                    ["상습체불", "임금체불", "예방", "상담 안내"],
                ),
                chunk(
                    "habitual-arrears-key-evidence",
                    amendment_title,
                    "상담 전 핵심 자료",
                    "임금체불 관련 상담 전에는 급여명세서, 입금내역, 근로계약서, 근무시간 기록, 사업주와의 대화자료를 모으는 것이 중요하다. 반복 지급 지연이나 금액 차이가 있다면 월별로 표를 만들어 설명한다.",
                    ["급여명세서", "입금내역", "근무시간 기록", "월별 정리"],
                ),
                chunk(
                    "habitual-arrears-nonjudgment",
                    amendment_title,
                    "법률 판단 주의",
                    "체불 여부, 고의성, 상습성 등은 행정기관이나 법률 전문가의 판단이 필요한 영역이다. BADA 챗봇은 '불법', '체불 확정'처럼 단정하지 않고 자료 기준의 차이와 준비할 질문을 안내한다.",
                    ["법률 판단", "상습성", "단정 금지", "질문 준비"],
                ),
            ],
        )
    )

    rights_title = "외국인근로자 권익보호를 위한 제도 안내문"
    docs.append(
        doc(
            "molab-foreign-worker-rights-protection-guide-ko",
            rights_title,
            "고용노동부",
            "official_guide",
            "ko",
            "한국어 안내문",
            [
                chunk(
                    "rights-guide-purpose",
                    rights_title,
                    "안내문 목적",
                    "외국인근로자 권익보호 안내문은 임금, 근로조건, 상담기관, 신고 절차 등 외국인근로자가 알아야 할 기본 정보를 제공한다. BADA는 이 내용을 바탕으로 상담 전 준비 항목을 다국어로 안내할 수 있다.",
                    ["외국인근로자", "권익보호", "근로조건", "상담기관"],
                ),
                chunk(
                    "rights-guide-wage",
                    rights_title,
                    "임금 관련 확인",
                    "임금 상담 전에는 약속한 임금, 실제 입금액, 급여명세서, 공제 항목, 지급일을 확인한다. 기숙사비, 식비, 작업복비 등 공제가 있다면 동의서나 설명 자료가 있었는지 함께 준비한다.",
                    ["임금", "급여명세서", "공제 항목", "기숙사비", "식비"],
                ),
                chunk(
                    "rights-guide-consultation",
                    rights_title,
                    "상담기관 이용",
                    "외국인근로자는 고용노동부, 외국인력상담센터, 지역 상담기관 등을 통해 상담을 받을 수 있다. 상담 전에는 언어 지원 필요 여부와 사건을 한 문단으로 요약한 내용을 준비하면 도움이 된다.",
                    ["고용노동부", "외국인력상담센터", "언어 지원", "사건 요약"],
                ),
                chunk(
                    "rights-guide-evidence-pack",
                    rights_title,
                    "증거 패키지 활용",
                    "상담 시에는 흩어진 자료보다 기간, 금액, 사업장 정보, 증빙 목록이 정리된 Evidence Pack이 유용하다. BADA 챗봇은 이 패키지에서 중요한 내용과 부족한 자료를 설명하는 역할을 한다.",
                    ["Evidence Pack", "증빙 목록", "부족한 자료", "상담 준비"],
                ),
            ],
        )
    )

    return {"documents": docs}


def foreign_worker_and_wage_claim_seed() -> dict:
    docs: list[dict] = []

    press_title = "임금체불 피해 외국인근로자 보호 강화"
    docs.append(
        doc(
            "molab-foreign-worker-wage-arrears-protection-joint-20251228",
            press_title,
            "고용노동부ㆍ법무부",
            "press_release",
            "ko",
            "2025-12-28 보도자료",
            [
                chunk(
                    "fw-wage-protection-overview",
                    press_title,
                    "보도자료 개요",
                    "임금체불 피해 외국인근로자 보호 강화 자료는 외국인근로자의 임금체불 피해를 줄이고 상담ㆍ구제 접근성을 높이는 방향을 설명한다. BADA에서는 사용자의 언어와 자료 수준에 맞춘 상담 전 준비 안내에 활용한다.",
                    ["임금체불", "외국인근로자", "보호 강화", "상담 접근성"],
                ),
                chunk(
                    "fw-wage-protection-cooperation",
                    press_title,
                    "기관 연계",
                    "외국인근로자 임금체불 문제는 고용노동부, 법무부, 상담센터 등 여러 기관의 안내가 함께 필요할 수 있다. 사용자는 체류 관련 불안과 임금 문제를 구분해 질문 목록을 준비하는 것이 좋다.",
                    ["고용노동부", "법무부", "상담센터", "체류", "임금 문제"],
                ),
                chunk(
                    "fw-wage-protection-evidence",
                    press_title,
                    "피해 확인 자료",
                    "상담 전에는 급여명세서, 계좌 입금내역, 근로계약서, 출퇴근 기록, 사업주 대화자료, 공제 설명자료를 모은다. 자료가 부족해도 현재 있는 자료와 없는 자료를 나누어 말하면 상담이 수월하다.",
                    ["급여명세서", "입금내역", "근로계약서", "출퇴근 기록", "공제 설명자료"],
                ),
                chunk(
                    "fw-wage-protection-language",
                    press_title,
                    "언어 지원",
                    "외국인근로자 상담에서는 모국어 설명이나 통역 지원이 중요하다. BADA 챗봇은 사용자가 입력한 언어를 고려해 사건 요약, 질문 목록, 준비자료를 같은 언어 또는 한국어 병기 형태로 안내하는 방향이 적절하다.",
                    ["언어 지원", "통역", "모국어", "다국어 챗봇"],
                ),
            ],
        )
    )

    wage_claim_title = "임금채권보장법"
    docs.append(
        doc(
            "law-wage-claim-guarantee-act-21137-20260512",
            wage_claim_title,
            "국가법령정보센터",
            "law",
            "ko",
            "법률 제21137호, 2026-05-12 시행",
            [
                chunk(
                    "wcga-purpose",
                    wage_claim_title,
                    "목적",
                    "임금채권보장법은 사업주가 임금 등을 지급하지 못하는 경우 근로자의 생활 안정을 지원하기 위한 제도와 절차를 정한다. BADA에서는 대지급금 관련 상담 전 필요한 자료를 정리하는 참고자료로 사용한다.",
                    ["임금채권보장법", "대지급금", "생활 안정", "자료 정리"],
                ),
                chunk(
                    "wcga-unpaid-wages",
                    wage_claim_title,
                    "체불 임금등",
                    "체불 임금등 관련 상담에서는 임금, 퇴직금, 휴업수당 등 어떤 금품이 문제인지, 어느 기간에 발생했는지, 어떤 자료로 확인할 수 있는지를 구분해야 한다. 최종 인정 여부는 관계기관의 확인이 필요하다.",
                    ["체불 임금등", "퇴직금", "휴업수당", "기간", "관계기관 확인"],
                ),
                chunk(
                    "wcga-substitute-payment",
                    wage_claim_title,
                    "대지급금 상담 준비",
                    "대지급금 상담을 준비할 때는 근무 기간, 퇴직 여부, 미지급 금액으로 보이는 내역, 사업주 정보, 신청서류와 첨부자료를 정리한다. BADA는 서류 목록과 질문 목록을 만드는 데 도움을 줄 수 있다.",
                    ["대지급금", "근무 기간", "퇴직 여부", "사업주 정보", "신청서류"],
                ),
                chunk(
                    "wcga-employer-confirmation",
                    wage_claim_title,
                    "사업주 확인서 관련",
                    "체불 임금등ㆍ사업주 확인서 발급신청과 관련해서는 사업장 정보, 근로자 정보, 임금 기간, 금액, 첨부자료를 준비해야 한다. 금액은 자료 기준으로 정리하고 법적 판단은 상담기관에 확인한다.",
                    ["사업주 확인서", "발급신청", "임금 기간", "첨부자료"],
                ),
                chunk(
                    "wcga-fraud-warning",
                    wage_claim_title,
                    "부정수급 주의",
                    "대지급금 등 제도는 사실관계를 정확히 확인하는 것이 중요하다. 사실과 다른 내용으로 신청하면 불이익이 발생할 수 있으므로, BADA는 수급 가능 여부를 단정하지 않고 자료 정리와 상담 준비에 한정해 안내한다.",
                    ["부정수급", "사실관계", "수급 가능 여부", "단정 금지"],
                ),
            ],
        )
    )

    employment_title = "외국인근로자 취업 안내"
    docs.append(
        doc(
            "easylaw-foreign-worker-employment-guide",
            employment_title,
            "생활법령정보",
            "public_guide",
            "ko",
            "외국인근로자 취업 안내",
            [
                chunk(
                    "employment-guide-overview",
                    employment_title,
                    "취업 안내 개요",
                    "외국인근로자 취업 안내자료는 취업 가능 체류자격, 고용절차, 근로계약, 사업장 변경 등 기본 정보를 설명한다. 임금 상담에서는 체류자격보다 실제 근무 사실과 임금 자료를 먼저 정리하는 것이 중요하다.",
                    ["외국인근로자 취업", "체류자격", "고용절차", "근로계약"],
                ),
                chunk(
                    "employment-guide-contract",
                    employment_title,
                    "근로계약 확인",
                    "근로계약서에는 임금, 근로시간, 업무, 근무 장소, 계약기간 등 상담의 핵심 정보가 들어간다. 한국어가 익숙하지 않은 사용자는 계약서 원문과 번역 내용을 함께 준비하면 좋다.",
                    ["근로계약서", "임금", "근로시간", "업무", "번역"],
                ),
                chunk(
                    "employment-guide-workplace-change",
                    employment_title,
                    "사업장 변경 상담",
                    "사업장 변경 관련 질문은 임금체불, 근무환경, 사업주와의 관계, 체류 절차가 함께 얽힐 수 있다. 상담 전에는 변경을 고민하게 된 사유와 관련 자료를 시간 순서로 정리한다.",
                    ["사업장 변경", "임금체불", "근무환경", "체류 절차"],
                ),
                chunk(
                    "employment-guide-support-center",
                    employment_title,
                    "상담기관",
                    "외국인근로자는 고용센터, 외국인력상담센터, 지역 상담기관 등에서 도움을 받을 수 있다. 상담 전에는 사건 요약, 질문 목록, 준비자료 목록을 만들어 가면 더 정확한 안내를 받을 수 있다.",
                    ["고용센터", "외국인력상담센터", "상담기관", "질문 목록"],
                ),
            ],
        )
    )

    guide_en_title = "Guide to Protecting the Rights of Foreign Workers"
    docs.append(
        doc(
            "molab-foreign-worker-rights-protection-guide-en",
            guide_en_title,
            "Ministry of Employment and Labor",
            "official_guide",
            "en",
            "English guide",
            [
                chunk(
                    "rights-guide-en-wages",
                    guide_en_title,
                    "Wages and payslips",
                    "Before consultation, foreign workers should prepare their employment contract, payslips, bank deposit records, working-hour records, and any explanation of deductions such as dormitory fees, meals, or uniforms.",
                    ["wages", "payslip", "bank deposit", "deductions"],
                    "en",
                ),
                chunk(
                    "rights-guide-en-consultation",
                    guide_en_title,
                    "Consultation preparation",
                    "It is helpful to summarize the workplace name, employment period, promised wage, actual payment, disputed period, and available evidence in one short paragraph before visiting a labor office or support center.",
                    ["consultation", "labor office", "evidence", "summary"],
                    "en",
                ),
                chunk(
                    "rights-guide-en-language",
                    guide_en_title,
                    "Language support",
                    "If Korean is difficult, workers should ask whether interpretation or multilingual support is available. BADA can help prepare a simple Korean summary and questions based on the user's own language.",
                    ["language support", "interpretation", "multilingual", "questions"],
                    "en",
                ),
            ],
        )
    )

    inspection_title = "외국인 고용 취약사업장 집중 감독"
    docs.append(
        doc(
            "molab-foreign-worker-vulnerable-workplace-inspection-20250903",
            inspection_title,
            "고용노동부",
            "press_release",
            "ko",
            "2025-09-03 보도자료",
            [
                chunk(
                    "inspection-overview",
                    inspection_title,
                    "감독 자료 개요",
                    "외국인 고용 취약사업장 집중 감독 자료는 외국인근로자의 임금, 근로조건, 근무환경 등 취약 요소를 점검하는 취지를 설명한다. BADA에서는 사용자가 상담 전 위험 신호와 자료를 정리하는 데 참고한다.",
                    ["취약사업장", "집중 감독", "외국인근로자", "근로조건"],
                ),
                chunk(
                    "inspection-wage-evidence",
                    inspection_title,
                    "임금 관련 점검자료",
                    "임금 관련 점검에는 급여명세서, 계좌 입금내역, 공제 내역, 근로계약서, 출퇴근 기록이 중요하다. 월별 차이가 있으면 같은 기간끼리 비교표를 만들어 상담기관에 보여주는 것이 좋다.",
                    ["급여명세서", "입금내역", "공제 내역", "비교표"],
                ),
                chunk(
                    "inspection-workplace-risk",
                    inspection_title,
                    "사업장 관련 확인",
                    "사업장 관련 상담에서는 사업장명, 주소, 대표자, 실제 근무 장소, 숙소 제공 여부, 업무 내용, 대화자료를 정리한다. BADA는 이 정보를 Evidence Pack의 핵심 요약과 누락자료 안내에 활용할 수 있다.",
                    ["사업장명", "주소", "숙소", "업무 내용", "대화자료"],
                ),
            ],
        )
    )

    return {"documents": docs}


def write_json(name: str, payload: dict) -> None:
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    path = SEED_DIR / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    documents = payload["documents"] if isinstance(payload, dict) else payload
    doc_count = len(documents)
    chunk_count = sum(len(document["chunks"]) for document in documents)
    print(f"wrote {path.relative_to(ROOT)} docs={doc_count} chunks={chunk_count}")


def main() -> None:
    write_json("labor_guides.json", labor_guides_seed())
    write_json("molab_subrogation_confirmation_application_form.json", subrogation_form_seed())
    write_json("bada_labor_forms_and_laws_20260612.json", labor_forms_and_laws_seed())
    write_json("bada_foreign_worker_and_wage_claim_20260612.json", foreign_worker_and_wage_claim_seed())


if __name__ == "__main__":
    main()
