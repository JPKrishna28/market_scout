import { useEffect, useState } from "react";
import { HiOutlineMoon, HiOutlineSun } from "react-icons/hi";

export default function ThemeToggle() {

const [theme,setTheme]=useState("dark");

useEffect(()=>{

const saved=localStorage.getItem("theme");

if(saved){
setTheme(saved);
document.documentElement.setAttribute("data-theme",saved);
}

},[]);

const toggleTheme=()=>{

const newTheme=theme==="dark"?"light":"dark";

setTheme(newTheme);
document.documentElement.setAttribute("data-theme",newTheme);
localStorage.setItem("theme",newTheme);

};

return(

<button
onClick={toggleTheme}
className="btn btn-secondary"
>

{theme==="dark" ? <HiOutlineSun/> : <HiOutlineMoon/>}

</button>

);
}