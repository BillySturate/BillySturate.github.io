var posts=["2022/09/13/HTML+CSS+JS/CSS基础总结/","2022/09/15/HTML+CSS+JS/CSS寄出之选择器进阶+背景属性+元素显示模式+三大特性/","2022/09/24/HTML+CSS+JS/CSS布局之盒子模型/","2022/09/29/HTML+CSS+JS/CSS布局之浮动/","2022/08/04/C++/C++const修饰指针的三种情况/","2022/09/08/HTML+CSS+JS/HTML基础总结/","2022/08/19/Json/JSON详解/","2022/07/11/Json/JSON+Shell/","2022/06/26/C++/C++lambada表达式/","2022/06/18/C++/C++函数指针/","2022/06/27/C++/C++mutable/","2022/08/18/C++/c++命名空间详解/","2022/08/18/C++/c++类型转换/","2022/08/28/Linux系统编程/Linux系统编程之IPC(进程间通信)/","2022/09/01/Linux系统编程/Linux系统编程之信号/","2022/07/14/C++/do-while(0)/","2022/09/05/Linux系统编程/Linux系统编程之守护进程、线程/","2022/08/22/Linux系统编程/Linux系统编程之文件IO/","2022/07/11/Linux/CMake详解/","2022/09/07/Linux系统编程/Linux系统编程之线程同步/","2022/07/11/Linux/GCC详解/","2022/08/11/Linux/Vim_Vi常用命令总结/","2022/08/26/Linux系统编程/Linux系统编程之进程/","2022/08/27/Linux系统编程/Linux系统编程之虚拟地址空间和文件描述符/","2022/06/02/Linux/Linux常用命令总结/","2022/08/12/Linux/gdb详解/","2022/06/15/Linux/解决win10下SecureCRT SSH连接慢的问题/","2022/10/11/Linux网络编程/Linux网络编程之三次握手四次挥手/","2022/10/05/Linux网络编程/Linux网路编程之Socket套接字/","2022/10/14/Linux网络编程/【Linux网络编程】TCP状态转换、半关闭、2MSL/","2022/11/21/Linux网络编程/【Linux网络编程】UDP服务器/","2022/11/11/Linux网络编程/【Linux网络编程】epoll反应堆/","2022/07/25/Python/Matplotlib详解/","2022/11/09/Linux网络编程/【Linux网络编程】epoll进阶/","2022/10/21/Linux网络编程/【Linux网络编程】多路IO转接之select、poll、epoll/","2022/11/20/Linux网络编程/【Linux网络编程】手写线程池/","2022/06/04/Robocup/Robocup3d比赛环境的搭建及常用函数简介/","2022/06/01/Markdown/Markdown语法/","2022/10/13/Linux网络编程/【Linux网络编程】多进程并发服务器、多线程并发服务器/","2022/07/17/Qt/QtUI/","2022/07/28/Python/Numpy/","2022/06/17/Qt/Qt学习笔记(上)/","2024/03/17/Python/Python 精简笔记/","2022/08/05/Python/pandas详解/","2022/06/17/Qt/Qt学习笔记(中)/","2022/06/19/VSCode/VSCode中文乱码问题的解决/","2022/06/17/Qt/Qt学习笔记(下)/","2022/09/12/VSCode/VSCode去掉拷贝来的代码前的行号/","2022/07/07/VSCode/VScode 调试教程 tasks.json和launch.json的设置/","2022/06/10/数据结构与算法/常用算法总结/","2022/08/02/人工智能/疲态检测/"];function toRandomPost(){pjax.loadUrl('/'+posts[Math.floor(Math.random() * posts.length)]);};