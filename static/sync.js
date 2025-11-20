async function fetchManifest() {
    let res = await fetch("/manifest");
    let manifest = await res.json();
  
    let list = document.getElementById("fileList");
    list.innerHTML = "";
    manifest.files.forEach(f => {
      let li = document.createElement("li");
      li.innerHTML = `<a href="/files/${f}">${f}</a>`;
      list.appendChild(li);
    });
  }
  
  document.getElementById("uploadForm").addEventListener("submit", async e => {
    e.preventDefault();
    let formData = new FormData(e.target);
    let res = await fetch("/upload", { method: "POST", body: formData });
    let data = await res.json();
    alert(data.message);
    fetchManifest();
  });
  
  async function fetchCloud() {
    let res = await fetch("/fetch_cloud", { method: "POST" });
    let data = await res.json();
    alert(data.message);
    fetchManifest();
  }
  
  window.onload = fetchManifest;
  