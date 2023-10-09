document.addEventListener("DOMContentLoaded", function() {
  
  var progressBar = document.querySelectorAll(".progress-bar");
  var time = 1500;
  

  progressBar.forEach(function(i) {
    let label = i.children[0];
    let line = i.children[1];
    let count = 0;
    let dataCount = label.getAttribute("data-count");
    let lineCount = line.children[0];
 
    let runTime = time/dataCount;
    
    let animationLineCount = setInterval(function(){
      if(count < dataCount){
        count++;
         label.innerHTML = "Project done";
        lineCount.style.width = count + '%';
      }
    },runTime);
  });
});
