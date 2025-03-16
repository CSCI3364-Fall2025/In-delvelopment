function showStudentView() {
    document.getElementById("studentView").style.display = "block";
    document.getElementById("professorView").style.display = "none";
}

function showProfessorView() {
    document.getElementById("studentView").style.display = "none";
    document.getElementById("professorView").style.display = "block";
}

function viewGrades() {
    let gradeResults = document.getElementById("gradeResults");
    gradeResults.style.display = "block";
    gradeResults.innerHTML = "<h3>Your Grades</h3><p>Contribution: Good</p><p>Teamwork: Excellent</p><p>Communication: Average</p><p>Comments: Keep up the good work!</p>";
}

function viewAssessmentResults() {
    let assessmentResults = document.getElementById("assessmentResults");
    assessmentResults.style.display = "block";
    assessmentResults.innerHTML = "<h3>Assessment Feedback</h3><p>Contribution: Good</p><p>Teamwork: Excellent</p><p>Communication: Average</p><p>Comments: Keep up the good work!</p><label for='professorScore'>Give Score (out of 10):</label><input type='number' id='professorScore' min='0' max='10'><button onclick='submitProfessorScore()'>Submit Score</button>";
}

function submitProfessorScore() {
    let score = document.getElementById("professorScore").value;
    alert("Score submitted: " + score);
}