
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, abort
)
from database import get_connection, initialize_database

app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-before-deployment"


@app.route("/")
def dashboard():
    connection = get_connection()

    total = connection.execute(
        "SELECT COUNT(*) FROM incidents"
    ).fetchone()[0]

    open_count = connection.execute(
        "SELECT COUNT(*) FROM incidents WHERE status = 'Open'"
    ).fetchone()[0]

    critical_count = connection.execute(
        "SELECT COUNT(*) FROM incidents WHERE severity = 'Critical' "
        "AND status != 'Resolved'"
    ).fetchone()[0]

    resolved_count = connection.execute(
        "SELECT COUNT(*) FROM incidents WHERE status = 'Resolved'"
    ).fetchone()[0]

    incidents = connection.execute(
        "SELECT * FROM incidents ORDER BY id DESC LIMIT 10"
    ).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        total=total,
        open_count=open_count,
        critical_count=critical_count,
        resolved_count=resolved_count,
        incidents=incidents
    )


@app.route("/report", methods=["GET", "POST"])
def report_incident():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        severity = request.form.get("severity", "").strip()
        reporter = request.form.get("reporter", "").strip()

        valid_severities = {"Low", "Medium", "High", "Critical"}

        if not all([title, category, description, severity, reporter]):
            flash("Please complete every field.", "error")
            return render_template("report_incident.html")

        if severity not in valid_severities:
            flash("Please select a valid severity.", "error")
            return render_template("report_incident.html")

        connection = get_connection()

        cursor = connection.execute(
            """
            INSERT INTO incidents
                (title, category, description, severity, reporter)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, category, description, severity, reporter)
        )

        incident_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO investigation_history
                (incident_id, action, notes)
            VALUES (?, ?, ?)
            """,
            (
                incident_id,
                "Incident reported",
                "Incident created and added to the tracker."
            )
        )

        connection.commit()
        connection.close()

        flash("Incident reported successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("report_incident.html")


@app.route("/incidents")
def incident_list():
    connection = get_connection()

    incidents = connection.execute(
        "SELECT * FROM incidents ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return render_template("incident_list.html", incidents=incidents)


@app.route("/incidents/<int:incident_id>", methods=["GET", "POST"])
def incident_details(incident_id):
    connection = get_connection()

    incident = connection.execute(
        "SELECT * FROM incidents WHERE id = ?",
        (incident_id,)
    ).fetchone()

    if incident is None:
        connection.close()
        abort(404)

    if request.method == "POST":
        status = request.form.get("status", "")
        notes = request.form.get("notes", "").strip()

        valid_statuses = {"Open", "Investigating", "Resolved"}

        if status not in valid_statuses or not notes:
            flash("Select a valid status and enter investigation notes.", "error")
        else:
            connection.execute(
                """
                UPDATE incidents
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, incident_id)
            )

            connection.execute(
                """
                INSERT INTO investigation_history
                    (incident_id, action, notes)
                VALUES (?, ?, ?)
                """,
                (incident_id, "Status updated to " + status, notes)
            )

            connection.commit()
            flash("Incident and investigation history updated.", "success")

        connection.close()
        return redirect(
            url_for("incident_details", incident_id=incident_id)
        )

    history = connection.execute(
        """
        SELECT * FROM investigation_history
        WHERE incident_id = ?
        ORDER BY id DESC
        """,
        (incident_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "incident_details.html",
        incident=incident,
        history=history
    )


@app.route("/investigation-history")
def investigation_history():
    connection = get_connection()

    history = connection.execute(
        """
        SELECT h.*, i.title AS incident_title
        FROM investigation_history h
        JOIN incidents i ON i.id = h.incident_id
        ORDER BY h.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "investigation_history.html",
        history=history
    )


@app.route("/settings")
def settings():
    return render_template("settings.html")


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
