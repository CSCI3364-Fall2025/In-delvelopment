import io.gatling.core.Predef._
import io.gatling.http.Predef._
import scala.concurrent.duration._

class StudentFacultySimulation extends Simulation {
  // Read users and duration from system properties so you can vary at runtime
  val users = Integer.getInteger("users", 100).toInt
  val ramp = Integer.getInteger("rampSeconds", 30).toInt

  val httpProtocol = http
    .baseUrl("http://localhost:8000")
    .inferHtmlResources()
    .acceptHeader("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    .userAgentHeader("Gatling")

  // Helper to login via the debug test_login form (DEBUG must be True in Django settings)
  val login = exec(
    http("GET test_login page")
      .get("/test_login")
      .check(regex("name='csrfmiddlewaretoken' value='([^']+)' ").saveAs("csrf"))
  ).pause(100.millis)
    .exec(
      http("POST test_login")
        .post("/test_login")
        .formParam("email", "loadtester@example.edu")
        .formParam("role", session => session("roleParam").as[String])
        .formParam("csrfmiddlewaretoken", "${csrf}")
        .check(status.in(200,302))
    )

  val studentScenario = scenario("StudentDashboard")
    .exec(session => session.set("roleParam", "student"))
    .exec(login)
    .pause(500.millis)
    .exec(http("Student: GET dashboard")
      .get("/dashboard/")
      .check(status.in(200,304))
    )
    .pause(1)
    .exec(http("Student: GET teams")
      .get("/assessments/teams")
      .check(status.in(200,304))
    )

  val facultyScenario = scenario("FacultyCourseDashboard")
    .exec(session => session.set("roleParam", "professor"))
    .exec(login)
    .pause(500.millis)
    .exec(http("Professor: GET course dashboard")
      .get("/assessments/courses")
      .check(status.in(200,304))
    )
    .pause(1)
    .exec(http("Professor: GET course detail (first course)")
      .get("/assessments/course/1/1/")
      .check(status.in(200,304)).silent
    )

  setUp(
    studentScenario.inject(rampUsers(users) during (ramp seconds)),
    facultyScenario.inject(rampUsers((users/10).max(1)) during (ramp seconds))
  ).protocols(httpProtocol)
}
