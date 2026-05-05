#include <iostream>
#include <memory>

int main()
{
  int i = 0;
  int *p1 = &i;
  int *p2 = &i;

  auto up1 = std::make_unique<int>(10);
  auto up2 = std::move(up1);
  // auto up2 = up1; ! WRONG

  auto up3 = std::make_shared<int>(10);
  auto up4 = up3;
  std::weak_ptr up5 = up3;
  // std::cout<< *up3 << " " << *up4 << " " << *up5<< std::endl;
  if (auto sp = up5.lock()) {   // ✅ 转成 shared_ptr
    std::cout << *up3 << " "
              << *up4 << " "
              << *sp << std::endl;
}
  
  std::cout << up3.use_count() << std::endl;
  
  *p1 = 2;
  std::cout<< *p2 << std::endl;
  
  return 0;
}