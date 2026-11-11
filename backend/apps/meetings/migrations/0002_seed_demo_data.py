"""
DEMO DATA SEED (data migration).

Populates a fresh database with two sample logins (member@example.com /
demo12345 as role=member, admin@example.com / demo12345 as role=admin) plus
~8-10 realistic meetings spanning different topics (sprint planning, budget
review, hiring, etc.), most with a generated MeetingSummary and a mix of
AI-generated and manually-added ActionItems (some done, some not) - so the
app is immediately explorable right after `migrate`, with no manual data
entry.

Calls the real `summarize_meeting_notes()` function (apps.common.ai) to
generate the seeded summaries/action items. At migrate time there is no
OPENAI_API_KEY configured, so this always runs in deterministic stub mode -
the same output anyone gets from a fresh `migrate` run.

Idempotent by design: every row is looked up with get_or_create (users,
meetings) or an explicit existence check (summaries/action items, which
have no natural unique key) before being created, so running `migrate` more
than once - or reapplying this migration - never produces duplicate rows.
"""
from datetime import date, timedelta

from django.contrib.auth.hashers import make_password
from django.db import migrations

from apps.common.ai import summarize_meeting_notes

MEMBER_EMAIL = "member@example.com"
ADMIN_EMAIL = "admin@example.com"
DEMO_PASSWORD = "demo12345"


def seed_demo_data(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Meeting = apps.get_model("meetings", "Meeting")
    MeetingSummary = apps.get_model("meetings", "MeetingSummary")
    ActionItem = apps.get_model("meetings", "ActionItem")

    today = date.today()

    # Historical models (from `apps.get_model`) only have the fields
    # captured in migration state - no set_password()/custom manager
    # methods from the real User class - so the password is hashed by hand.
    member, _ = User.objects.get_or_create(
        email=MEMBER_EMAIL,
        defaults={
            "full_name": "Morgan Member", "role": "member", "is_active": True,
            "password": make_password(DEMO_PASSWORD),
        },
    )
    admin, _ = User.objects.get_or_create(
        email=ADMIN_EMAIL,
        defaults={
            "full_name": "Avery Admin", "role": "admin", "is_active": True,
            "is_staff": True,
            "password": make_password(DEMO_PASSWORD),
        },
    )

    def get_or_create_meeting(title, days_ago, raw_notes, creator):
        meeting, _ = Meeting.objects.get_or_create(
            title=title, created_by=creator,
            defaults={
                "meeting_date": today - timedelta(days=days_ago),
                "raw_notes": raw_notes,
            },
        )
        return meeting

    def ensure_ai_summary(meeting):
        """Mirrors MeetingViewSet.summarize: generate via the real
        summarize_meeting_notes() (stub mode at migrate time, since no
        OPENAI_API_KEY is configured), then create/replace the summary and
        the AI-generated action items only."""
        result = summarize_meeting_notes(meeting.raw_notes)
        MeetingSummary.objects.update_or_create(
            meeting=meeting, defaults={"summary": result["summary"]},
        )
        if not meeting.action_items.filter(is_ai_generated=True).exists():
            for description in result["action_items"]:
                ActionItem.objects.create(
                    meeting=meeting, description=description, is_ai_generated=True,
                )

    def ensure_manual_action_item(meeting, description, assignee, is_done=False):
        if not meeting.action_items.filter(description=description, is_ai_generated=False).exists():
            ActionItem.objects.create(
                meeting=meeting, description=description, assignee=assignee,
                is_done=is_done, is_ai_generated=False,
            )

    # 1. Sprint planning - summarized, with a manually-added item too.
    sprint_planning = get_or_create_meeting(
        "Sprint 42 Planning", 2,
        "We reviewed the backlog for sprint 42. The team agreed to prioritize "
        "the checkout redesign and defer the notifications revamp to next "
        "sprint. QA raised concerns about test coverage on the payments "
        "module. Priya will investigate the flaky integration tests before "
        "Thursday. We also discussed velocity trends from the last three "
        "sprints and agreed they're stabilizing around 32 points.",
        member,
    )
    ensure_ai_summary(sprint_planning)
    ensure_manual_action_item(sprint_planning, "Book a follow-up with QA on test coverage", "Priya", is_done=False)

    # 2. Budget review - summarized, one item marked done.
    budget_review = get_or_create_meeting(
        "Q3 Budget Review", 10,
        "Finance presented Q3 actuals versus budget. Marketing spend came in "
        "9% under budget due to a delayed campaign launch. Engineering "
        "headcount costs are tracking to plan. Leadership approved a $40k "
        "reallocation from marketing to the infrastructure upgrade project. "
        "Next quarter's budget draft is due to finance by the 15th.",
        admin,
    )
    ensure_ai_summary(budget_review)
    ensure_manual_action_item(budget_review, "Submit infrastructure upgrade budget line item", "Chen", is_done=True)

    # 3. Hiring discussion - summarized.
    hiring = get_or_create_meeting(
        "Backend Engineer Hiring Debrief", 5,
        "The panel discussed the two final candidates for the senior backend "
        "role. Candidate A showed strong system design skills but limited "
        "Django experience. Candidate B has direct experience with our stack "
        "and strong references. The panel leans towards extending an offer "
        "to candidate B. HR needs to confirm the salary band before an offer "
        "goes out.",
        member,
    )
    ensure_ai_summary(hiring)

    # 4. Customer feedback review - summarized, with a done manual item.
    customer_feedback = get_or_create_meeting(
        "Monthly Customer Feedback Review", 15,
        "Support shared the top five recurring complaints from last month: "
        "slow page loads on the dashboard, confusing export options, missing "
        "bulk-edit for tags, unclear error messages on failed imports, and "
        "requests for dark mode. Product will scope the dashboard "
        "performance work first since it affects the most users. Design "
        "will mock up a revised export flow for review next week.",
        member,
    )
    ensure_ai_summary(customer_feedback)
    ensure_manual_action_item(customer_feedback, "Share dashboard performance findings with engineering", "Dana", is_done=True)

    # 5. Marketing campaign kickoff - summarized.
    marketing_kickoff = get_or_create_meeting(
        "Spring Campaign Kickoff", 20,
        "Marketing kicked off planning for the spring campaign. The theme "
        "will center on the new collaboration features launched last month. "
        "Budget is capped at $75k across paid social and email. Creative "
        "assets are due from the agency in three weeks. We agreed to run a "
        "soft launch to the existing customer list before the public push.",
        admin,
    )
    ensure_ai_summary(marketing_kickoff)

    # 6. Incident postmortem - summarized, with an undone manual item.
    postmortem = get_or_create_meeting(
        "Incident Postmortem - Checkout Outage", 7,
        "The team reviewed last Tuesday's 40-minute checkout outage. Root "
        "cause was a misconfigured connection pool limit after a deploy. "
        "The on-call engineer caught it within 12 minutes but the rollback "
        "took longer than expected. We agreed to add an automated alert on "
        "connection pool saturation and to document the rollback steps more "
        "clearly in the runbook.",
        member,
    )
    ensure_ai_summary(postmortem)
    ensure_manual_action_item(postmortem, "Update the on-call runbook with clearer rollback steps", None, is_done=False)

    # 7. Roadmap planning - summarized.
    roadmap = get_or_create_meeting(
        "H2 Roadmap Planning", 25,
        "Leadership walked through the draft H2 roadmap. Three themes "
        "emerged: improving onboarding conversion, reducing support ticket "
        "volume through better in-app guidance, and expanding the reporting "
        "API for enterprise customers. Each theme needs an owner and a "
        "rough sizing estimate before the roadmap is finalized next month.",
        admin,
    )
    ensure_ai_summary(roadmap)

    # 8. One-on-one - not yet summarized (demonstrates the un-summarized state).
    get_or_create_meeting(
        "1:1 - Morgan & Manager", 1,
        "Discussed current workload and upcoming performance review cycle. "
        "Morgan flagged interest in picking up more frontend work next "
        "quarter. No blockers reported this week.",
        member,
    )

    # 9. Vendor contract review - summarized.
    vendor_review = get_or_create_meeting(
        "Vendor Contract Renewal Review", 30,
        "Procurement reviewed the renewal terms for our analytics vendor. "
        "The proposed renewal includes a 12% price increase. Legal flagged "
        "an outdated data retention clause that needs to be updated before "
        "signing. We'll request a revised contract and aim to close within "
        "two weeks.",
        admin,
    )
    ensure_ai_summary(vendor_review)

    # 10. All-hands recap - summarized, with a done and an undone manual item.
    all_hands = get_or_create_meeting(
        "Company All-Hands Recap", 3,
        "The CEO reviewed Q3 highlights including the successful launch of "
        "the collaboration features and the new enterprise customer "
        "onboarding. The CFO gave a brief update on runway and hiring plans "
        "for next year. Several teams presented demos of work in progress. "
        "A recording and slide deck will be shared company-wide.",
        member,
    )
    ensure_ai_summary(all_hands)
    ensure_manual_action_item(all_hands, "Share the all-hands recording and slides in the team channel", "Priya", is_done=True)
    ensure_manual_action_item(all_hands, "Collect follow-up questions for next month's all-hands", None, is_done=False)


def unseed_demo_data(apps, schema_editor):
    """Reverse migration: deleting the demo users cascades to every meeting,
    summary and action item created for them (all CASCADE FKs)."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(email__in=[MEMBER_EMAIL, ADMIN_EMAIL]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("meetings", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_data, unseed_demo_data),
    ]
