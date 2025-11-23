//Global JS function for greeting
function greet() {
  //Get user input
  let inputName = document.getElementById("name").value;

  //Call Go Greet function
  window.go.main.App.ListContainers().then((result) => {
    //Display result from Go
    console.log(result);

    const ul = document.getElementById("containers");
    for (let container of result) {
      console.log(container);
      const li = document.createElement("li");
      li.textContent = container.Names[0] + " (" + container.Image + ")";
      ul.appendChild(li);
    }
    document.getElementById("result").innerHTML = result.length;
  }).catch((err) => {
    console.log(err);
  }).finally(() => {
    console.log("finished!");
  });
}

function selectInputFolder() {
  window.go.main.App.SelectDirectory().then((result) => {
    console.log(result);
    if (result != "") {
      document.getElementById("input_folder").value = result;
    }
  }).catch((err) => {
    console.log(err);
  }).finally(() => {
    console.log("finished!");
  });
}
function selectOutputFolder() {
  window.go.main.App.SelectDirectory().then((result) => {
    console.log(result);
    if (result != "") {
      document.getElementById("output_folder").value = result;
    }
  }).catch((err) => {
    console.log(err);
  }).finally(() => {
    console.log("finished!");
  });
}

function updateThreadsNumber() {
  const threadsNumber = document.getElementById("threads-number");
  threadsNumber.textContent =
    document.getElementById("threads-number-input").value;
}

function Run() {
  console.log();
}
