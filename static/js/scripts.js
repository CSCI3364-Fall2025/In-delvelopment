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

// New functions to calculate average grade and display comments
function calculateAverageGrade(grades) {
    if (grades.length === 0) return "N/A";
    let total = grades.reduce((sum, grade) => sum + grade, 0);
    return (total / grades.length).toFixed(2);
}

function displayComments(comments, elementId) {
    let commentsList = document.getElementById(elementId);
    commentsList.innerHTML = "";
    comments.forEach(comment => {
        let li = document.createElement("li");
        li.textContent = comment;
        commentsList.appendChild(li);
    });
}

// Function to handle flagging for self-assessment
function flagSelfAssessment() {
    let flag = document.getElementById("flagSelfAssessment").checked;
    if (flag) {
        alert("This item has been flagged for self-assessment.");
    } else {
        alert("This item has been unflagged for self-assessment.");
    }
}

// Function to handle manual grade submission
function submitManualGrade() {
    let manualGrade = document.getElementById("manualGrade").value;
    if (manualGrade < 0 || manualGrade > 10) {
        alert("Please enter a valid grade between 0 and 10.");
    } else {
        alert("Manual grade submitted: " + manualGrade);
    }
}

// Example usage
let studentGrades = [4, 3, 2]; // Example grades
let studentComments = ["Great team player!", "Needs improvement in communication."]; // Example comments

document.getElementById("averageGrade").textContent = calculateAverageGrade(studentGrades);
displayComments(studentComments, "commentsList");

let professorGrades = [4, 3, 3]; // Example grades
let professorComments = ["Excellent performance.", "Good teamwork."]; // Example comments

document.getElementById("averageGradeProf").textContent = calculateAverageGrade(professorGrades);
displayComments(professorComments, "commentsListProf");

// Add event listener for flagging self-assessment
document.getElementById("flagSelfAssessment").addEventListener("change", flagSelfAssessment);