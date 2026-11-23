"""All text content for the Constitution Ai website.

Edit this file to change what the pages say. Guides contain general legal
information for India, reviewed November 2026; laws change, so re-check them
before relying on them.
"""

SITE = {
    "name": "Constitution Ai",
    "tagline": "Plain-language legal help, on demand",
    # Shown on the Contact page and footer only when filled in.
    "contact_email": "",
    "contact_phone": "",
    "location": "",
}

DISCLAIMER = (
    "Constitution Ai gives general legal information, not legal advice. It is not a lawyer, it can make "
    "mistakes, and using it does not create a lawyer-client relationship. Check anything important "
    "against official sources and talk to a qualified lawyer before you act."
)

PROVIDERS = ["Groq", "Google Gemini", "OpenRouter", "Ollama", "DeepSeek", "OpenAI", "Anthropic Claude",
             "xAI Grok", "DeepInfra", "Hive"]

LANGUAGES = ["English", "Hindi", "Bengali", "Marathi", "Tamil", "Telugu", "Gujarati", "Kannada", "Spanish", "French"]

STATS = [
    {"label": "PRACTICE AREAS", "number": "6", "suffix": ""},
    {"label": "ANSWER LANGUAGES", "number": "10", "suffix": ""},
    {"label": "AI PROVIDERS SUPPORTED", "number": "10", "suffix": "+"},
    {"label": "AVAILABLE", "number": "24", "suffix": "/7"},
]

AREAS = [
    {
        "slug": "tenancy-property",
        "title": "Tenancy & Property",
        "short": "Deposits, rent agreements, eviction notices and property paperwork.",
        "image": "area-tenancy.svg",
        "icon": "home",
        "tags": ["Security deposits", "Eviction notices", "Rent agreements"],
        "intro": [
            "Most tenancy problems come down to what the agreement says, what notice was given, and what proof you "
            "have. Constitution Ai helps you read your rent agreement, understand your rights as a tenant or "
            "landlord, and plan the next step, from a polite reminder to a legal notice or a civil suit.",
            "It also explains property paperwork in plain words: what a sale deed or lease needs, when a document "
            "must be registered, and which questions to ask before you sign.",
        ],
        "covers": [
            "Getting a security deposit back",
            "Eviction and notice periods",
            "Rent increases and repairs",
            "Registering leases and sale deeds",
        ],
        "laws": [
            ("Transfer of Property Act, 1882", "General rules on leases, including notice to end a tenancy (Section 106)."),
            ("State rent control laws", "For example the Delhi Rent Control Act, 1958 or the Maharashtra Rent Control Act, 1999."),
            ("Model Tenancy Act, 2021", "A model law that applies only where a state has adopted it."),
            ("Registration Act, 1908", "Leases for more than one year must be registered (Section 17)."),
        ],
        "questions": [
            "My landlord won't return my security deposit. What can I do?",
            "How much notice must my landlord give before asking me to leave?",
            "Does my 11-month rent agreement need to be registered?",
        ],
    },
    {
        "slug": "consumer-rights",
        "title": "Consumer Rights",
        "short": "Defective products, poor service, refunds and online shopping disputes.",
        "image": "area-consumer.svg",
        "icon": "cart",
        "tags": ["Refunds", "E-commerce", "Consumer commission"],
        "intro": [
            "Bought something defective, paid for a service that was never delivered, or stuck with an online "
            "seller who won't refund? Consumer law gives you simple, low-cost routes to a remedy, and in most "
            "cases you don't need a lawyer.",
            "Constitution Ai explains whether your problem counts as a defect, a deficiency in service or an unfair "
            "trade practice, which consumer commission to approach, and how to file online.",
        ],
        "covers": [
            "Defective goods and deficient services",
            "Online shopping and delivery disputes",
            "Filing on the e-Daakhil portal",
            "Writing a complaint and a demand letter",
        ],
        "laws": [
            ("Consumer Protection Act, 2019", "Rights of consumers and the three-tier consumer commissions."),
            ("Consumer Protection (E-Commerce) Rules, 2020", "Duties of online marketplaces and sellers."),
            ("National Consumer Helpline", "Call 1915 or use consumerhelpline.gov.in to try to resolve it first."),
        ],
        "questions": [
            "How do I file a consumer complaint against a company for a defective product?",
            "An online seller won't refund a cancelled order. What can I do?",
            "Which consumer commission should I approach for a ₹2 lakh claim?",
        ],
    },
    {
        "slug": "police-criminal",
        "title": "Police & Criminal Matters",
        "short": "FIRs, police complaints, rights on arrest and the new criminal laws.",
        "image": "area-police.svg",
        "icon": "shield",
        "tags": ["FIR & Zero FIR", "Rights on arrest", "BNS · BNSS · BSA"],
        "intro": [
            "Since 1 July 2024, India's criminal law runs on three new codes: the Bharatiya Nyaya Sanhita (BNS), "
            "the Bharatiya Nagarik Suraksha Sanhita (BNSS) and the Bharatiya Sakshya Adhiniyam (BSA). They replaced "
            "the IPC, the CrPC and the Indian Evidence Act.",
            "Constitution Ai explains how to report a crime, what to do if the police won't register your "
            "complaint, and what your rights are if you or someone close to you is arrested. For anything urgent, "
            "call 112 first, and get a criminal lawyer for any arrest or charge.",
        ],
        "covers": [
            "Registering an FIR or a Zero FIR",
            "What to do if the police refuse",
            "Rights on arrest and detention",
            "Understanding the new criminal codes",
        ],
        "laws": [
            ("Bharatiya Nagarik Suraksha Sanhita, 2023", "Criminal procedure; an FIR is registered under Section 173."),
            ("Bharatiya Nyaya Sanhita, 2023", "Defines offences and punishments (replaced the IPC)."),
            ("Bharatiya Sakshya Adhiniyam, 2023", "Rules of evidence (replaced the Indian Evidence Act)."),
            ("Constitution of India, Article 22", "Protection against arbitrary arrest and detention."),
        ],
        "questions": [
            "The police are refusing to register my complaint. What are my options?",
            "What is a Zero FIR and how do I file one?",
            "What are my rights if the police arrest me?",
        ],
    },
    {
        "slug": "family-marriage",
        "title": "Family & Marriage",
        "short": "Divorce, maintenance, custody and protection from domestic violence.",
        "image": "area-family.svg",
        "icon": "family",
        "tags": ["Mutual consent divorce", "Maintenance", "Domestic violence"],
        "intro": [
            "Family disputes are personal and stressful. Constitution Ai explains the options calmly: how mutual "
            "consent divorce works, how maintenance is claimed, how courts think about child custody, and what "
            "protection the law offers against domestic violence.",
            "Family law depends on your personal law and the court you are in, so treat the answers as a starting "
            "point for a conversation with a family lawyer. If you are in danger, call 112 or the women's "
            "helpline 181.",
        ],
        "covers": [
            "Mutual consent and contested divorce",
            "Maintenance for spouses, children and parents",
            "Child custody and guardianship",
            "Protection orders under the DV Act",
        ],
        "laws": [
            ("Hindu Marriage Act, 1955", "Divorce by mutual consent under Section 13B, among other grounds."),
            ("Special Marriage Act, 1954", "Civil marriage and divorce for any couple."),
            ("Protection of Women from Domestic Violence Act, 2005", "Protection, residence and monetary relief orders."),
            ("Guardians and Wards Act, 1890", "Guardianship and custody of children."),
        ],
        "questions": [
            "How does mutual consent divorce work, and how long does it take?",
            "How can I claim maintenance for myself and my child?",
            "What protection does the Domestic Violence Act give me?",
        ],
    },
    {
        "slug": "employment-wages",
        "title": "Employment & Wages",
        "short": "Unpaid salary, termination, workplace harassment and labour rights.",
        "image": "area-employment.svg",
        "icon": "work",
        "tags": ["Unpaid salary", "Termination", "POSH"],
        "intro": [
            "Constitution Ai helps employees and small employers understand their rights at work: what to do about "
            "unpaid salary or dues, whether a termination followed the rules, and how to raise a complaint of "
            "sexual harassment at the workplace.",
            "India's labour law is moving to four labour codes, so it helps to check which rules apply to your job, "
            "your state and your employer. Constitution Ai can walk you through that and draft a clear written "
            "demand to your employer.",
        ],
        "covers": [
            "Recovering unpaid salary and dues",
            "Notice, resignation and termination",
            "Workplace sexual harassment (POSH) complaints",
            "Provident fund and gratuity questions",
        ],
        "laws": [
            ("Four Labour Codes", "Code on Wages, 2019; Industrial Relations Code, 2020; Code on Social Security, 2020; OSH Code, 2020."),
            ("Sexual Harassment of Women at Workplace Act, 2013", "Requires an Internal Committee at workplaces with 10 or more employees."),
            ("Your employment contract", "Notice periods, dues and policies usually start here."),
        ],
        "questions": [
            "My employer hasn't paid my last two months of salary. What can I do?",
            "Can my employer fire me without notice?",
            "How do I file a sexual harassment complaint at my workplace?",
        ],
    },
    {
        "slug": "money-cheques-contracts",
        "title": "Money, Cheques & Contracts",
        "short": "Cheque bounce cases, loans, recovering money and everyday contracts.",
        "image": "area-money.svg",
        "icon": "rupee",
        "tags": ["Cheque bounce", "Money recovery", "Contracts"],
        "intro": [
            "When someone owes you money, timing matters. A bounced cheque has strict deadlines, and most claims to "
            "recover money must be filed within a fixed time. Constitution Ai explains those deadlines, what proof "
            "you need, and how to draft a demand notice.",
            "It also helps you understand everyday contracts before you sign them: what a clause really means, "
            "what is missing, and what to negotiate.",
        ],
        "covers": [
            "Cheque bounce under Section 138",
            "Recovering money lent to someone",
            "Reading and checking contracts",
            "Time limits for filing a case",
        ],
        "laws": [
            ("Negotiable Instruments Act, 1881", "Cheque dishonour is an offence under Section 138."),
            ("Indian Contract Act, 1872", "When agreements are enforceable and what happens on breach."),
            ("Limitation Act, 1963", "Time limits for filing suits; many money claims must be filed within three years."),
        ],
        "questions": [
            "A cheque given to me has bounced. What should I do now?",
            "How can I recover money I lent to a friend?",
            "Can you check this contract clause before I sign?",
        ],
    },
]

CASES = [
    {
        "slug": "security-deposit",
        "title": "Security deposit withheld",
        "area": "tenancy-property",
        "image": "case-deposit.svg",
        "summary": "A tenant moved out two months ago and the landlord still hasn't returned a ₹40,000 deposit.",
        "situation": "Riya rented a flat on an 11-month agreement, gave one month's notice and handed back the keys. "
                     "The landlord keeps saying he will \"pay next week\" and now claims vague repair costs.",
        "helps": [
            "Reads the rent agreement to find the refund and deduction clauses",
            "Lists the proof to gather: payment receipts, move-out photos, messages",
            "Drafts a firm reminder and then a legal notice with a clear deadline",
            "Explains the options if there is still no refund, such as a civil suit for recovery",
        ],
        "question": "My landlord hasn't returned my ₹40,000 security deposit two months after I moved out. What can I do?",
    },
    {
        "slug": "defective-phone",
        "title": "Defective phone, no refund",
        "area": "consumer-rights",
        "image": "case-refund.svg",
        "summary": "A new phone stopped working in a week and the online seller refuses a refund or replacement.",
        "situation": "Arjun bought a phone online. It stopped charging after six days, and the seller and the brand "
                     "keep sending him to each other.",
        "helps": [
            "Explains whether this is a defect under the Consumer Protection Act, 2019",
            "Suggests trying the National Consumer Helpline (1915) first",
            "Shows how to file on e-Daakhil and which commission to choose",
            "Drafts the complaint with the facts, documents and relief to ask for",
        ],
        "question": "My new phone stopped working after a week and the online seller refuses a refund. How do I file a consumer complaint?",
    },
    {
        "slug": "police-refuse-fir",
        "title": "Police won't register an FIR",
        "area": "police-criminal",
        "image": "case-fir.svg",
        "summary": "A theft victim was turned away from the police station and told to \"come back later\".",
        "situation": "Meera's scooter was stolen outside her office. At the police station she was told to search "
                     "for it herself first and come back in a few days.",
        "helps": [
            "Explains that theft is a cognizable offence and an FIR must be registered under Section 173 BNSS",
            "Explains Zero FIR and e-FIR options",
            "Drafts a written complaint to the Superintendent of Police",
            "Explains the next step before a Magistrate if the police still refuse",
        ],
        "question": "My scooter was stolen and the police are refusing to register an FIR. What should I do?",
    },
    {
        "slug": "unpaid-salary",
        "title": "Two months of unpaid salary",
        "area": "employment-wages",
        "image": "case-salary.svg",
        "summary": "An employee resigned and the company is holding back the last two months' pay.",
        "situation": "Sameer served his notice period, but his employer says the final settlement is \"under "
                     "process\" and has stopped replying to emails.",
        "helps": [
            "Checks the appointment letter and resignation terms",
            "Lists the dues usually included in a full and final settlement",
            "Drafts a written demand to HR with a deadline",
            "Explains complaints to the labour authorities and other remedies",
        ],
        "question": "My employer hasn't paid my last two months of salary after I resigned. What can I do?",
    },
    {
        "slug": "cheque-bounce",
        "title": "A bounced cheque",
        "area": "money-cheques-contracts",
        "image": "case-cheque.svg",
        "summary": "A buyer paid by cheque for goods and the cheque came back unpaid.",
        "situation": "Kiran sold equipment and received a cheque for ₹1.5 lakh. The bank returned it with the memo "
                     "\"funds insufficient\".",
        "helps": [
            "Explains the strict 30-day window to send a demand notice",
            "Drafts the demand notice under Section 138 of the NI Act",
            "Explains the 15-day payment period and when to file the complaint",
            "Lists the documents the court will want to see",
        ],
        "question": "A ₹1.5 lakh cheque I received has bounced for insufficient funds. What are my next steps?",
    },
    {
        "slug": "mutual-divorce",
        "title": "Mutual consent divorce",
        "area": "family-marriage",
        "image": "case-divorce.svg",
        "summary": "A couple has agreed to separate and wants to know the process and timeline.",
        "situation": "A couple married under the Hindu Marriage Act has lived apart for over a year and agreed on "
                     "maintenance and custody.",
        "helps": [
            "Explains divorce by mutual consent under Section 13B",
            "Lists what the joint petition and settlement usually cover",
            "Explains the cooling-off period and when courts may waive it",
            "Lists the questions to ask a family lawyer",
        ],
        "question": "We both agree to a divorce and have lived apart for over a year. How does mutual consent divorce work?",
    },
]

GUIDES = [
    {
        "slug": "how-to-send-a-legal-notice",
        "title": "How to send a legal notice",
        "category": "Getting started",
        "image": "guide-notice.svg",
        "summary": "What a legal notice is, when the law requires one, and what to put in it.",
        "tags": ["Legal notice", "Civil disputes", "Drafting"],
        "body": [
            ("p", "A legal notice is a formal letter that sets out your grievance, says what you want, and gives the "
                  "other side time to fix it before you go to court. It often resolves a dispute on its own, and it "
                  "creates a written record that you tried to settle."),
            ("h", "Is a legal notice compulsory?"),
            ("p", "For most private disputes it is not compulsory, but it is a good practice. In some situations the "
                  "law requires a notice before you can act:"),
            ("ul", [
                "Before suing the government or a public officer for an official act, two months' notice is required "
                "(Section 80, Code of Civil Procedure, 1908).",
                "For a bounced cheque, a written demand must be sent within 30 days of learning that the cheque was "
                "dishonoured (Section 138, Negotiable Instruments Act, 1881).",
                "To end a monthly tenancy, notice must be given as required by the agreement or Section 106 of the "
                "Transfer of Property Act, 1882.",
            ]),
            ("h", "What to include"),
            ("ul", [
                "Full names and addresses of both sides",
                "The facts in order, with dates and amounts",
                "The documents you rely on (agreement, receipts, messages)",
                "Exactly what you want: payment, refund, repair, or to stop doing something",
                "A clear deadline, often 15 to 30 days",
                "What you will do if they don't comply",
            ]),
            ("h", "How to send it"),
            ("p", "Send it by registered post with acknowledgement due or by speed post, and keep the receipt and "
                  "tracking printout. Sending a copy by email or messaging app as well helps prove delivery. A "
                  "lawyer's letterhead is not required, but it can add weight."),
            ("quote", "Keep a copy of everything you send and receive. In most disputes, the side with better "
                      "records is in the stronger position."),
            ("h", "After you send it"),
            ("p", "If they reply, read the reply carefully: it may be an opening for settlement. If they ignore it, "
                  "the next step depends on the dispute, for example a consumer commission, a civil court, or a "
                  "Magistrate in a cheque case. Constitution Ai can draft a notice for you to review."),
        ],
    },
    {
        "slug": "filing-an-fir-under-bnss",
        "title": "Filing an FIR under the BNSS",
        "category": "Police & criminal",
        "image": "guide-fir.svg",
        "summary": "How FIRs, Zero FIRs and e-FIRs work under the 2024 criminal laws, and what to do if the police refuse.",
        "tags": ["FIR", "BNSS", "Police"],
        "body": [
            ("p", "Since 1 July 2024, a First Information Report (FIR) is registered under Section 173 of the "
                  "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS), which replaced Section 154 of the Code of "
                  "Criminal Procedure. An FIR starts a police investigation into a cognizable offence, such as theft, "
                  "assault or cheating."),
            ("h", "How to file"),
            ("ul", [
                "Go to the police station and give the information orally or in writing. If oral, it is written "
                "down and read back to you before you sign.",
                "Zero FIR: you can file at any police station, even if the crime happened elsewhere. It is then "
                "transferred to the right station.",
                "e-FIR: information can be given electronically, and it is taken on record once you sign it within "
                "three days.",
                "You are entitled to a free copy of the FIR.",
            ]),
            ("h", "If the police refuse"),
            ("p", "Send the substance of your complaint in writing, by post, to the Superintendent of Police. If that "
                  "does not work, you can apply to the Magistrate under Section 175(3) BNSS (earlier Section 156(3) "
                  "CrPC) asking for the police to be directed to investigate."),
            ("quote", "For offences punishable with three to seven years, the police may first conduct a "
                      "preliminary enquiry, which should be completed within 14 days."),
            ("h", "Non-cognizable offences"),
            ("p", "For minor, non-cognizable offences, the police record the information in a register and refer you "
                  "to the Magistrate; they cannot investigate without the Magistrate's order."),
            ("p", "In an emergency, call 112. If you are accused of an offence or arrested, contact a criminal lawyer "
                  "or your District Legal Services Authority for free legal aid."),
        ],
    },
    {
        "slug": "consumer-complaints-made-simple",
        "title": "Consumer complaints made simple",
        "category": "Consumer rights",
        "image": "guide-consumer.svg",
        "summary": "Where and how to file a complaint under the Consumer Protection Act, 2019, and the deadlines.",
        "tags": ["Consumer", "e-Daakhil", "Refunds"],
        "body": [
            ("p", "If a product is defective, a service is deficient, or a seller uses an unfair trade practice, the "
                  "Consumer Protection Act, 2019 lets you complain to a consumer commission. You can file and argue "
                  "the case yourself; a lawyer is not compulsory."),
            ("h", "Before you file"),
            ("ul", [
                "Write to the seller or service provider with the facts and what you want, and keep the reply.",
                "Try the National Consumer Helpline: call 1915 or use consumerhelpline.gov.in.",
                "Collect your bill, warranty card, order emails, photos and chats.",
            ]),
            ("h", "Which commission"),
            ("ul", [
                "District Commission: when the value of goods or services paid for is up to ₹50 lakh.",
                "State Commission: above ₹50 lakh and up to ₹2 crore.",
                "National Commission: above ₹2 crore.",
            ]),
            ("p", "You can file where the opposite party lives or does business, where the problem arose, or where "
                  "you live or work."),
            ("h", "How to file"),
            ("p", "Complaints can be filed online on the e-Daakhil portal (edaakhil.nic.in). No court fee is charged "
                  "for claims up to ₹5 lakh."),
            ("quote", "File within two years of the problem arising (Section 69). A late complaint needs a good "
                      "reason for the delay."),
        ],
    },
    {
        "slug": "cheque-bounce-section-138",
        "title": "Cheque bounce: the Section 138 timeline",
        "category": "Money & contracts",
        "image": "guide-cheque.svg",
        "summary": "The strict deadlines for a bounced cheque case and the documents you need.",
        "tags": ["Cheque bounce", "NI Act", "Deadlines"],
        "body": [
            ("p", "When a cheque given to pay a legally enforceable debt is returned unpaid, for example for "
                  "insufficient funds, the drawer can be prosecuted under Section 138 of the Negotiable Instruments "
                  "Act, 1881. The deadlines are strict, so act quickly."),
            ("h", "The timeline"),
            ("ul", [
                "Present the cheque within its validity period (three months from its date).",
                "Send a written demand notice within 30 days of receiving the bank's return memo.",
                "The drawer has 15 days from receiving the notice to pay.",
                "If they don't pay, file a complaint before the Magistrate within one month after those 15 days end.",
            ]),
            ("h", "Where to file"),
            ("p", "Generally in the court with jurisdiction over the branch of your bank where you presented the "
                  "cheque for collection."),
            ("h", "Documents to keep"),
            ("ul", [
                "The original cheque and the bank's return memo",
                "A copy of the demand notice and proof of posting and delivery",
                "Proof of the debt: invoice, agreement, loan record or messages",
            ]),
            ("quote", "The punishment can be imprisonment of up to two years, a fine of up to twice the cheque "
                      "amount, or both. The court may also order interim compensation of up to 20%."),
        ],
    },
    {
        "slug": "getting-your-security-deposit-back",
        "title": "Getting your security deposit back",
        "category": "Tenancy & property",
        "image": "guide-deposit.svg",
        "summary": "How to protect your deposit when you move out, and what to do if the landlord won't refund it.",
        "tags": ["Tenancy", "Security deposit", "Rent agreement"],
        "body": [
            ("p", "A security deposit belongs to the tenant. The landlord can usually keep only what the agreement "
                  "allows, such as unpaid rent or the cost of damage beyond normal wear and tear."),
            ("h", "Before you move out"),
            ("ul", [
                "Give notice in writing, as the agreement requires.",
                "Take dated photos or a video of every room and of meter readings.",
                "Hand over the keys and get a written acknowledgement.",
                "Ask in writing for the deposit and any deductions to be explained.",
            ]),
            ("h", "If it isn't refunded"),
            ("ul", [
                "Send a written reminder, then a legal notice with a deadline.",
                "If there is still no refund, you can file a civil suit for recovery of the money.",
                "In states that have adopted a law based on the Model Tenancy Act, 2021, a Rent Authority may also help.",
            ]),
            ("quote", "Under the Model Tenancy Act, 2021, the deposit for a home is capped at two months' rent, but "
                      "it applies only where a state has adopted it. Check your state's law."),
            ("p", "A suit to recover money generally has to be filed within three years. Landlord and tenant "
                  "disputes are usually not consumer complaints."),
        ],
    },
    {
        "slug": "free-legal-aid-in-india",
        "title": "Free legal aid in India",
        "category": "Getting started",
        "image": "guide-aid.svg",
        "summary": "Who can get a free lawyer, and how to ask for one.",
        "tags": ["Legal aid", "NALSA", "Lok Adalat"],
        "body": [
            ("p", "Article 39A of the Constitution directs the State to provide free legal aid so that no one is "
                  "denied justice because of poverty or other disabilities. The Legal Services Authorities Act, 1987 "
                  "puts this into practice through legal services authorities at every level."),
            ("h", "Who is eligible"),
            ("p", "Under Section 12 of the Act, free legal services are available to, among others:"),
            ("ul", [
                "Women and children",
                "Members of Scheduled Castes and Scheduled Tribes",
                "Victims of trafficking or forced labour",
                "Persons with disabilities",
                "Victims of mass disasters, ethnic violence, caste atrocities and natural or industrial disasters",
                "Industrial workers",
                "People in custody",
                "People whose annual income is below the limit set by the government",
            ]),
            ("h", "How to ask"),
            ("ul", [
                "Visit the District Legal Services Authority (DLSA) at your district court, or the Taluk Legal Services Committee.",
                "Call the NALSA helpline on 15100 or visit nalsa.gov.in.",
                "Ask about Lok Adalats, where disputes can be settled without court fees.",
            ]),
            ("quote", "If you are arrested and cannot afford a lawyer, you have the right to free legal aid. Ask the "
                      "police or the court for a legal aid lawyer."),
        ],
    },
]

FAQS = [
    ("Is this legal advice?",
     "No. Constitution Ai gives general legal information to help you understand your situation and options. It "
     "can make mistakes. For anything with serious consequences, such as an arrest, a court date, a large sum or "
     "custody, talk to a qualified lawyer."),
    ("Is it free to use?",
     "The website is free. Answers come from the AI provider chosen on the server. Some providers, such as Groq, "
     "Google Gemini and OpenRouter's free models, have free plans with daily limits; others charge for usage."),
    ("Which laws does it know?",
     "It is tuned for India and knows the 2024 criminal laws (BNS, BNSS and BSA), but it can also answer general "
     "questions for the US, UK, Canada and Australia. You can upload the actual text of an Act as a reference "
     "dataset so answers quote real sections."),
    ("Is my information private?",
     "Your chats are saved in your own browser. Each question is sent to the AI provider that answers it, so "
     "avoid sharing ID numbers, bank details or anything you would not put in an email."),
    ("Can it read my documents?",
     "Yes. Attach a PDF, Word file, text file or a photo of a notice, contract, FIR or court order, and ask what it "
     "means for you."),
    ("Can it draft a legal notice or complaint?",
     "Yes. It can draft notices, complaints, replies and lists of questions for your lawyer. Treat them as drafts "
     "and have them reviewed before you send or file them."),
]


def area(slug):
    return next((a for a in AREAS if a["slug"] == slug), None)


def case(slug):
    return next((c for c in CASES if c["slug"] == slug), None)


def guide(slug):
    return next((g for g in GUIDES if g["slug"] == slug), None)
